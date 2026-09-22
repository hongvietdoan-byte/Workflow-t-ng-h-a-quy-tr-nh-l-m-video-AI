import json
import os
import shutil
import struct
import tempfile
import unittest
import zlib

from core import assets, diag
from core.adapters.clipai import ClipAIVideoProvider
from core.db import connect
from core.llm_io import approve_motion_prompt, store_motion_prompts, store_scene_analysis
from core.pipeline import Pipeline
from core.providers import MockVideoProvider
from core.runner import VideoRunner
from tests.test_adapters import TOKEN, FakeTransport, ctx_of, ok
from tests.test_llm_io_preflight import ANALYSIS


def png(seed):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00" + bytes([seed, 0, 0]))) + chunk(b"IEND", b""))


class ClipAISubmitTests(unittest.TestCase):
    """Step 4's video generation carries the same resource-library reference pictures Step 2 already sends to Deepix — no separate
    Subject Library upload/approval needed for this."""

    def setUp(self):
        self.t = FakeTransport()
        self.p = ClipAIVideoProvider(TOKEN, "https://clipai.example", self.t)
        self.dir = tempfile.mkdtemp()
        self.img = os.path.join(self.dir, "frame.png")
        with open(self.img, "wb") as f:
            f.write(b"x")
        self.t.on("POST", "/api/kling/seedance-video-submit", ok({"tasks": [{"task_id": "t1", "task_status": "submitted"}]}))
        self.t.on("POST", "/api/kling/omni-video-submit", ok({"tasks": [{"task_id": "t1", "task_status": "submitted"}]}))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def ref(self, name, seed, role="character"):
        path = os.path.join(self.dir, name)
        with open(path, "wb") as f:
            f.write(png(seed))
        return {"path": path, "label": os.path.splitext(name)[0].upper(), "role": role}

    def test_local_reference_pictures_are_uploaded_and_tied_to_a_named_person(self):
        refs = [self.ref("kelly.png", 1), self.ref("kenta.png", 2)]
        self.p.submit(self.img, "Kelly and Kenta talk", None, 5, "seedance", image_references=refs)
        call = self.t.calls[0]
        ctx = ctx_of(call)
        roles = [(c["type"], c.get("role"), c.get("image_url", {}).get("url")) for c in ctx["content"][1:]]
        self.assertEqual(roles, [("image_url", "first_frame", ""), ("image_url", "reference_image", ""),
                                 ("image_url", "reference_image", "")])
        self.assertEqual(call["body"].count(b'name="image_files"'), 3)                 # first frame + 2 local references
        text = ctx["content"][0]["text"]
        self.assertIn("@Image 2 is KELLY", text)
        self.assertIn("@Image 3 is KENTA", text)
        self.assertIn("do not swap or blend", text)

    def test_a_location_reference_gets_its_own_wording(self):
        refs = [self.ref("dao.png", 1, role="location")]
        self.p.submit(self.img, "hero on the island", None, 5, "seedance", image_references=refs)
        text = ctx_of(self.t.calls[0])["content"][0]["text"]
        self.assertIn("@Image 2 is the location DAO", text)
        self.assertNotIn("swap or blend", text)                                        # only one person -> no mixing warning needed

    def test_a_missing_local_file_is_skipped_not_fatal(self):
        refs = [self.ref("kelly.png", 1), {"path": os.path.join(self.dir, "gone.png"), "label": "GONE", "role": "character"}]
        self.p.submit(self.img, "x", None, 5, "seedance", image_references=refs)
        ctx = ctx_of(self.t.calls[0])
        self.assertEqual(sum(1 for c in ctx["content"] if c["type"] == "image_url"), 2)   # first_frame + only the readable one
        self.assertNotIn("GONE", ctx["content"][0]["text"])

    def test_local_pictures_and_subject_library_entries_share_one_budget_locals_first(self):
        refs = [self.ref(f"c{i}.png", i) for i in range(8)]                            # exactly the cap for non-2.5 seedance
        subjects = [{"name": "Extra", "uri": "asset://extra"}]
        self.p.submit(self.img, "x", None, 5, "seedance", image_references=refs, subjects=subjects)
        ctx = ctx_of(self.t.calls[0])
        urls = [c.get("image_url", {}).get("url") for c in ctx["content"][1:]]
        self.assertEqual(len(urls), 9)                                                 # first frame + 8 locals
        self.assertEqual(urls.count(""), 9)                                            # all local: no room left for the subject
        self.assertNotIn("asset://extra", json.dumps(ctx))                             # the subject library entry did not fit

    def test_a_subject_library_entry_fills_whatever_room_the_local_pictures_leave(self):
        refs = [self.ref("kelly.png", 1)]
        subjects = [{"name": "Extra", "uri": "asset://extra"}]
        self.p.submit(self.img, "x", None, 5, "seedance", image_references=refs, subjects=subjects)
        ctx = ctx_of(self.t.calls[0])
        urls = [c.get("image_url", {}).get("url") for c in ctx["content"][1:]]
        self.assertEqual(urls, ["", "", "asset://extra"])                              # first frame, local pic, then the subject

    def test_kling_omni_is_unaffected_by_image_references(self):
        refs = [self.ref("kelly.png", 1)]
        self.p.submit(self.img, "x", None, 5, "kling", image_references=refs)
        self.assertNotIn("reference_image", json.dumps(ctx_of(self.t.calls[0])))


class VideoRunnerWiringTests(unittest.TestCase):
    """core/runner.py: the video job actually receives this project's chosen resource pictures, the same way Step 2 does."""

    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        os.environ["ASSET_DIR"] = os.path.join(self.data, "assets")
        self.pid = self.p.create_project("t")
        self.scene = self.p.create_scene(self.pid, 1, "S1")
        store_scene_analysis(self.p, self.pid, ANALYSIS)
        img = self.p.create_job(self.scene)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        os.makedirs(os.path.join(self.data, str(self.pid), "images"))
        open(os.path.join(self.data, str(self.pid), "images", f"job_{img}.png"), "wb").close()
        store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "push in"}]})
        approve_motion_prompt(self.p, self.scene)

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.data, ignore_errors=True)

    def submit(self, model):
        self.p.set_video_model(self.pid, model)
        provider = MockVideoProvider()
        self.p.create_job(self.scene, "video_gen")
        VideoRunner(self.p, provider, self.data).submit_pending(self.pid)
        return list(provider._tasks.values())[-1]

    def test_a_chosen_character_asset_reaches_the_seedance_job_without_any_subject_library_setup(self):
        a = assets.create(self.p.conn, "FF", "character", "Lyra", "", "", None, "x")
        assets.add_image(self.p.conn, a, "lyra.png", png(1))
        assets.attach(self.p.conn, self.pid, a)
        task = self.submit("seedance")
        self.assertEqual([r["label"] for r in task["image_references"]], ["Lyra"])
        self.assertEqual(task["subjects"], [])                                          # never touched the Subject Library

    def test_kling_gets_no_image_references(self):
        a = assets.create(self.p.conn, "FF", "character", "Lyra", "", "", None, "x")
        assets.add_image(self.p.conn, a, "lyra.png", png(1))
        assets.attach(self.p.conn, self.pid, a)
        task = self.submit("kling")
        self.assertEqual(task["image_references"], [])

    def test_a_reference_picture_deleted_from_disk_does_not_crash_the_submit(self):
        # assets._row() already drops a picture whose file is gone before scene_references() ever sees it (same rule Step 2's
        # image gen relies on), so this asset simply contributes no reference here rather than a broken path reaching Clip AI.
        a = assets.create(self.p.conn, "FF", "character", "Lyra", "", "", None, "x")
        path = assets.add_image(self.p.conn, a, "lyra.png", png(1))
        assets.attach(self.p.conn, self.pid, a)
        os.remove(path)
        task = self.submit("seedance")
        self.assertEqual(task["image_references"], [])


if __name__ == "__main__":
    unittest.main()
