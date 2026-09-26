"""Deepix picture models per project (GPT Image 2.5 Sunburst / Flare added 2026-09-24) and their rules checked before sending (W10)."""
import json
import os
import re
import tempfile
import unittest

from core import image_models
from core.adapters.deepix import DeepixImageProvider
from core.db import connect
from core.pipeline import Pipeline
from core.providers import ProviderError
from tests.test_adapters import FakeTransport, field_of, ok

TOKEN = "x" * 40


def has_field(call, name):
    return re.search(rf'name="{name}"\r\n', call["body"].decode("utf-8", "replace")) is not None


class RuleTests(unittest.TestCase):
    def test_the_new_gpt_models_are_listed_with_their_limits(self):
        for m in ("gpt-image-2.5-sunburst", "gpt-image-2.5-flare"):
            self.assertIn(m, image_models.models())
            self.assertEqual(image_models.max_refs(m), 16)
        self.assertEqual(image_models.max_refs(image_models.DEFAULT), 10)

    def test_sizes_follow_each_model(self):
        gpt, seed = "gpt-image-2.5-sunburst", image_models.DEFAULT
        for ok_size in ("2048x1152", "1152x2048", "3840x2160", "auto", None):
            self.assertIsNone(image_models.size_problem(gpt, ok_size), ok_size)
        self.assertIn("tỉ lệ", image_models.size_problem(gpt, "3072x768"))          # 4:1 — fine for Seedream, not for GPT
        self.assertIsNone(image_models.size_problem(seed, "3072x768"))
        self.assertIn("cạnh dài", image_models.size_problem(gpt, "4096x2304"))
        self.assertIn("bội số", image_models.size_problem(gpt, "2050x1152"))
        self.assertIn("pixel", image_models.size_problem(seed, "auto"))              # Seedream needs pixels
        self.assertIn("tổng pixel", image_models.size_problem(seed, "1024x512"))

    def test_the_project_choice_wins_over_the_default(self):
        p = Pipeline(connect())
        pid = p.create_project("t")
        self.assertEqual(image_models.of_project(p.project(pid)), image_models.DEFAULT)
        p.set_project_field(pid, "image_model", "gpt-image-2.5-flare")
        self.assertEqual(image_models.of_project(p.project(pid)), "gpt-image-2.5-flare")


class DeepixModelTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.t.on("POST", "/api/image-generator/conversation-create", ok({"msg_id": 1}))
        self.p = DeepixImageProvider(TOKEN, "https://deepix.example", self.t)

    def test_the_model_of_the_job_is_sent_and_auto_size_is_left_out(self):
        self.p.submit("a hero", size="1152x2048", model="gpt-image-2.5-sunburst")
        call = self.t.calls[-1]
        self.assertEqual(field_of(call, "model"), "gpt-image-2.5-sunburst")
        self.assertEqual(field_of(call, "size"), "1152x2048")
        self.p.submit("a hero", size="auto", model="gpt-image-2.5-flare")
        self.assertFalse(has_field(self.t.calls[-1], "size"))
        self.assertEqual(self.p.usage_info("gpt-image-2.5-flare"), ("gpt-image-2.5-flare", "image"))

    def test_a_size_the_model_refuses_is_stopped_before_sending(self):
        with self.assertRaises(ProviderError) as e:
            self.p.submit("a hero", size="3072x768", model="gpt-image-2.5-sunburst")
        self.assertEqual(e.exception.code, "bad_size")
        self.assertEqual(self.t.calls, [])

    def test_up_to_16_references_for_gpt_10_for_seedream(self):
        d = tempfile.mkdtemp()
        refs = []
        for i in range(20):
            path = os.path.join(d, f"r{i}.jpg")
            open(path, "wb").write(b"\xff\xd8\xff" + bytes([i]) * 10)
            refs.append(path)
        count = lambda call: call["body"].count(b'name="file[]"')  # noqa: E731
        self.p.submit("x", refs[:16], model="gpt-image-2.5-sunburst")
        self.assertEqual(count(self.t.calls[-1]), 16)
        self.p.submit("x", refs[:10])
        self.assertEqual(count(self.t.calls[-1]), 10)
        sent = len(self.t.calls)
        for model in ("gpt-image-2.5-sunburst", None):      # 2026-09-26: more than the model takes is refused, not cut (the prompt
            with self.assertRaises(ProviderError):           # numbers the pictures — a cut list shifts every "Image N is …")
                self.p.submit("x", refs, model=model)
        self.assertEqual(len(self.t.calls), sent)


class RunnerModelTests(unittest.TestCase):
    def test_image_jobs_use_the_project_model_and_record_it(self):
        from core.runner import ImageRunner
        p = Pipeline(connect())
        pid = p.create_project("t")
        p.set_project_field(pid, "image_model", "gpt-image-2.5-sunburst")
        p.conn.execute("INSERT INTO scenes (project_id, idx, title, state, data) VALUES (?,?,?,?,?)",
                       (pid, 1, "s", "ready", json.dumps({"image_prompt": "a hero on a roof"})))
        sid = p.conn.execute("SELECT id FROM scenes").fetchone()["id"]
        p.conn.commit()
        t = FakeTransport()
        t.on("POST", "/api/image-generator/conversation-create", ok({"msg_id": 7}))
        runner = ImageRunner(p, DeepixImageProvider(TOKEN, "https://deepix.example", t), tempfile.mkdtemp())
        p.create_job(sid, "image_gen")
        runner.submit_pending(pid)
        self.assertEqual(field_of(t.calls[-1], "model"), "gpt-image-2.5-sunburst")
        job = p.conn.execute("SELECT model FROM jobs WHERE scene_id=?", (sid,)).fetchone()
        self.assertEqual(job["model"], "gpt-image-2.5-sunburst")
        used = p.conn.execute("SELECT model FROM usage_events WHERE kind='image'").fetchone()
        self.assertEqual(used["model"], "gpt-image-2.5-sunburst")


if __name__ == "__main__":
    unittest.main()
