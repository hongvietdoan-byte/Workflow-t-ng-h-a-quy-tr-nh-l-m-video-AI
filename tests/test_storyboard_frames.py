"""Deepix storyboard through the API, the web Weave Canvas way (prompt_key 14): frame 1 with the shared references, frames 2..N with
the references + frame 1; submit + ledger always in the calling thread (the first real run lost 3 paid frames to a thread error)."""
import json
import os
import re
import tempfile
import threading
import unittest

from core import storyboard_frames
from core.adapters.deepix import DeepixImageProvider
from core.providers import TaskStatus
from tests.test_adapters import FakeTransport, ok


class FakeStoryboard:
    name = "fake"

    def __init__(self):
        self.sent = []
        self.threads = set()

    def submit_storyboard_frame(self, prompt, refs, story, sid, index, size_, mode, mapping, size=None, model=None):
        self.threads.add(threading.get_ident())
        self.sent.append({"index": index, "refs": list(refs), "mode": mode, "mapping": mapping, "sid": sid})
        return f"m{index}"

    def status(self, mid):
        return TaskStatus("succeeded")

    def download(self, mid, dest):
        with open(dest, "wb") as f:
            f.write(mid.encode())
        return dest


class RunTests(unittest.TestCase):
    def test_frame_one_is_the_anchor_and_the_ledger_stays_in_this_thread(self):
        d = tempfile.mkdtemp()
        ref = os.path.join(d, "kelly.png")
        open(ref, "wb").close()
        prov, ledger = FakeStoryboard(), []
        res = storyboard_frames.run(prov, ["a", "b", "c", "d"], [{"path": ref, "label": "KELLY"}], "story", os.path.join(d, "out"),
                                    on_submit=lambda i, m: ledger.append((i, threading.get_ident())), poll=0, sleep=lambda s: None)
        self.assertEqual([f["error"] for f in res["frames"]], [None] * 4)
        self.assertEqual(prov.sent[0]["refs"], [ref])
        first = res["frames"][0]["path"]
        for s in prov.sent[1:]:
            self.assertEqual(s["refs"], [ref, first])
            self.assertEqual(s["mode"], "global")
            self.assertIn("continuity anchor", s["mapping"])
        self.assertEqual({t for _, t in ledger}, {threading.get_ident()})
        self.assertEqual(prov.threads, {threading.get_ident()})
        self.assertEqual(len({s["sid"] for s in prov.sent}), 1)

    def test_without_shared_references_each_frame_follows_the_previous(self):
        d = tempfile.mkdtemp()
        prov = FakeStoryboard()
        res = storyboard_frames.run(prov, ["a", "b", "c"], [], "story", d, poll=0, sleep=lambda s: None)
        paths = [f["path"] for f in res["frames"]]
        self.assertEqual(prov.sent[1]["refs"], [paths[0]])
        self.assertEqual(prov.sent[2]["refs"], [paths[0], paths[1]])
        self.assertEqual(prov.sent[2]["mode"], "sequential")


class AdapterTests(unittest.TestCase):
    def test_storyboard_frame_request_matches_the_web_canvas(self):
        t = FakeTransport()
        t.on("POST", "/api/image-generator/conversation-create", ok({"msg_id": 77}))
        d = tempfile.mkdtemp()
        ref = os.path.join(d, "k.png")
        with open(ref, "wb") as f:
            f.write(b"\x89PNG-fake")
        prov = DeepixImageProvider("tok", "https://deepix.example", t, model="gpt-image-2.5-sunburst", size="1152x2048")
        mid = prov.submit_storyboard_frame("frame prompt", [ref], "the story", "sb_1", 2, 4, "global", "Reference image mapping: ...")
        self.assertEqual(mid, "77")
        body = t.calls[0]["body"].decode("utf-8", "replace")
        field = lambda name: re.search(rf'name="{name}"\r\n\r\n(.*?)\r\n--', body, re.S).group(1)  # noqa: E731
        self.assertEqual((field("prompt_key"), field("message_type")), ("14", "storyboard"))
        keys = {p["key"]: p["text"] for p in json.loads(field("prompts"))}
        self.assertEqual(keys["frame_index"], "2")
        self.assertEqual(keys["group_size"], "4")
        self.assertEqual(keys["ref_mode"], "global")
        self.assertEqual(keys["storyboard_size_profile"], "clipai-video")
        self.assertIn('name="file[]"', body)


class SceneModeTests(unittest.TestCase):
    """Feature storyboard_api: the shots of a script scene become one storyboard in the runner — widest shot first (anchor), the others
    wait for it and go out with the shared references + the anchor picture and the storyboard fields."""
    def test_the_runner_draws_a_scene_as_one_storyboard(self):
        from unittest import mock
        from core import batch, llm_io, llm_runner
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        from tests.test_v3 import kenta_project

        class StoryboardMock(MockImageProvider):
            supports_storyboard = True

            def __init__(self):
                super().__init__()
                self.boards = {}

            def submit(self, prompt, references=None, size=None, model=None, storyboard=None):
                task = super().submit(prompt, references, size)
                self.boards[task] = storyboard
                return task

        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        llm_io.lock_character_bible(p, pid)
        data = tempfile.mkdtemp()
        prov = StoryboardMock()
        with mock.patch.dict(os.environ, {"FEATURE_STORYBOARD_API": "1"}):
            runner = ImageRunner(p, prov, data)
            runner.max_concurrent = 99
            batch.queue_images(p, pid)
            runner.submit_pending(pid)
            first_round = dict(prov.boards)
            runner.poll_once(pid)
            runner.submit_pending(pid)
        from core import scene_storyboard
        g = scene_storyboard.group_of(p.conn, pid, next(iter(r["id"] for r in p.conn.execute(
            "SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (pid,)))))
        self.assertIsNotNone(g)
        anchors = {b["storyboard_id"] for b in first_round.values() if b}
        self.assertTrue(first_round)
        self.assertTrue(all(b is not None and b["ref_mode"] in ("global", "sequential") for b in first_round.values()))
        later = {t: b for t, b in prov.boards.items() if t not in first_round}
        self.assertTrue(later)                                                  # the other shots went out after their anchor
        for task, b in later.items():
            self.assertIn(b["storyboard_id"], anchors)                          # same storyboard as the anchor of their scene
            self.assertTrue(any("scene anchor" not in r and os.path.basename(r).startswith("job_") for r in prov.references[task]))
            self.assertIn("continuity anchor", b["image_mapping"])
        self.assertEqual(len(first_round), len({s["story_scene"] for s in
                                                (json.loads(r["data"]) for r in p.conn.execute("SELECT data FROM scenes WHERE project_id=?",
                                                                                               (pid,)))} ))   # one anchor per scene

    def test_off_by_default_or_without_a_storyboard_provider(self):
        from core import scene_storyboard
        self.assertFalse(scene_storyboard.enabled())


if __name__ == "__main__":
    unittest.main()
