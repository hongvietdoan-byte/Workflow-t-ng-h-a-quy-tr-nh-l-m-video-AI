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


if __name__ == "__main__":
    unittest.main()
