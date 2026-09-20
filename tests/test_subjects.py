import json
import os
import re
import tempfile
import unittest

from core import subjects
from core.adapters.clipai import ClipAIVideoProvider
from core.adapters.clipai_subjects import ClipAISubjectLibrary, MockSubjectLibrary, is_active
from core.db import connect
from core.llm_io import approve_motion_prompt, store_motion_prompts, store_scene_analysis
from core.pipeline import Pipeline
from core.providers import MockVideoProvider, ProviderError
from core.runner import VideoRunner
from tests.test_adapters import TOKEN, FakeTransport, HttpResponse, ctx_of, ok
from tests.test_llm_io_preflight import ANALYSIS

ACTIVE = {"id": 1, "asset_id": "asset-A", "asset_uri": "asset://asset-A", "name": "FF_Lyra", "provider_status": "active",
          "asset_type": "image"}


def image(name="lyra.png"):
    path = os.path.join(tempfile.mkdtemp(), name)
    with open(path, "wb") as f:
        f.write(b"\x89PNG-fake")
    return path


class LibraryAdapterTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.lib = ClipAISubjectLibrary(TOKEN, "https://clipai.example", self.t, sleep=lambda s: None,
                                        poll_sec=1, timeout_sec=5)

    def routes(self, *list_pages):
        pages = list(list_pages)
        self.t.on("GET", "/api/kling/seedance-user-asset-list",
                  lambda call: ok({"count": len(pages[0]), "assets": pages.pop(0) if len(pages) > 1 else pages[0]}))
        self.t.on("POST", "/api/kling/seedance-user-asset-upload", ok(None))

    def test_upload_snapshots_ids_then_finds_the_new_active_asset_by_exact_name(self):
        old = {**ACTIVE, "asset_id": "asset-OLD", "asset_uri": "asset://asset-OLD", "name": "FF_Lyra"}  # same name, old id
        processing = {**ACTIVE, "provider_status": "processing", "asset_uri": None}
        self.routes([old], [old], [old, processing], [old, ACTIVE])
        asset = self.lib.upload(image(), "FF_Lyra")
        self.assertEqual((asset["asset_id"], asset["asset_uri"]), ("asset-A", "asset://asset-A"))
        post = next(c for c in self.t.calls if c["method"] == "POST")
        body = post["body"].decode("utf-8", "replace")
        self.assertIn('name="name"', body)
        self.assertIn("FF_Lyra", body)
        self.assertIn('filename="lyra.png"', body)
        self.assertEqual(post["headers"]["Authorization"], f"Bearer {TOKEN}")

    def test_failed_asset_reports_provider_message_and_is_not_retried(self):
        failed = {**ACTIVE, "provider_status": "failed", "provider_status_msg": "real person detected", "asset_uri": None}
        self.routes([], [failed])
        with self.assertRaises(ProviderError) as e:
            self.lib.upload(image(), "FF_Lyra")
        self.assertEqual((e.exception.code, str(e.exception)), ("asset_failed", "real person detected"))
        self.assertEqual(sum(1 for c in self.t.calls if c["method"] == "POST"), 1)

    def test_timeout_is_a_transient_soft_error(self):
        self.routes([], [{**ACTIVE, "provider_status": "processing", "asset_uri": None}])
        with self.assertRaises(ProviderError) as e:
            self.lib.upload(image(), "FF_Lyra")
        self.assertEqual((e.exception.code, e.exception.transient), ("timeout", True))

    def test_input_validation_sends_nothing(self):
        for path, name in ((image("x.gif"), "n"), (image(), "  "), (image(), "n" * 129), ("missing.png", "n")):
            with self.assertRaises(ProviderError):
                self.lib.upload(path, name)
        self.assertEqual(self.t.calls, [])

    def test_only_a_fully_active_asset_counts(self):
        self.assertTrue(is_active(ACTIVE))
        self.assertFalse(is_active({**ACTIVE, "asset_uri": ""}))
        self.assertFalse(is_active({**ACTIVE, "provider_status": "processing"}))

    def test_list_and_get(self):
        self.routes([ACTIVE])
        self.assertEqual(self.lib.get("asset-A")["name"], "FF_Lyra")
        self.assertIsNone(self.lib.get("asset-Z"))
        query = next(c["url"] for c in self.t.calls if c["method"] == "GET")
        self.assertIn("page_size=100", query)


class SeedanceSubmitTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.t.on("POST", "*", ok({"tasks": [{"task_id": "S", "task_status": "submitted"}]}))
        self.p = ClipAIVideoProvider(TOKEN, "https://clipai.example", self.t)
        self.img = image()
        self.subj = [{"name": "Lyra", "uri": "asset://asset-A"}, {"name": "Kael", "uri": "asset://asset-B"}]

    def test_subjects_become_reference_images_after_the_first_frame_with_a_stated_job(self):
        self.p.submit(self.img, "Lyra walks", None, 5, "seedance", False, self.subj)
        ctx = ctx_of(self.t.calls[0])
        roles = [(c["type"], c.get("role"), c.get("image_url", {}).get("url")) for c in ctx["content"][1:]]
        self.assertEqual(roles, [("image_url", "first_frame", ""), ("image_url", "reference_image", "asset://asset-A"),
                                 ("image_url", "reference_image", "asset://asset-B")])
        text = ctx["content"][0]["text"]
        self.assertIn("@Image 2 is the reference for Lyra", text)
        self.assertIn("@Image 3 is the reference for Kael", text)

    def test_kling_and_no_subjects_are_unchanged(self):
        self.p.submit(self.img, "x", None, 5, "kling", False, self.subj)
        self.assertNotIn("asset://", json.dumps(ctx_of(self.t.calls[0])))
        self.p.submit(self.img, "x", None, 5, "seedance")
        self.assertEqual(len(ctx_of(self.t.calls[1])["content"]), 2)

    def test_reference_cap_leaves_room_for_the_first_frame(self):
        many = [{"name": f"C{i}", "uri": f"asset://a{i}"} for i in range(20)]
        self.p.submit(self.img, "x", None, 5, "seedance", False, many)
        self.p.submit(self.img, "x", None, 5, "seedance-2.5", False, many)
        images = lambda c: sum(1 for x in ctx_of(c)["content"] if x["type"] == "image_url")
        self.assertEqual((images(self.t.calls[0]), images(self.t.calls[1])), (9, 20 + 1))  # 2.0: <= 9 ; 2.5: up to 30


class CharacterLinkTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.scene = self.p.create_scene(self.pid, 1, "S1")
        store_scene_analysis(self.p, self.pid, ANALYSIS)  # scene 1 cast: Lyra

    def test_link_unlink_refresh_and_scene_selection(self):
        subjects.link(self.p, self.pid, "Lyra", {**ACTIVE, "provider_status": "processing", "asset_uri": None})
        self.assertEqual(subjects.usable_for_scene(self.p, self.scene, 8), [])  # not active: never used
        lib = MockSubjectLibrary()
        subjects.link(self.p, self.pid, "Lyra", {"asset_id": "asset-mock-1", "provider_status": "processing"})
        self.assertEqual(subjects.refresh(self.p, self.pid, lib), 1)
        self.assertEqual(subjects.usable_for_scene(self.p, self.scene, 8), [{"name": "Lyra", "uri": "asset://asset-mock-1"}])
        subjects.link(self.p, self.pid, "Nữ chiến binh Amazon", ACTIVE)  # not in the scene's cast
        self.assertEqual(len(subjects.usable_for_scene(self.p, self.scene, 8)), 1)
        subjects.unlink(self.p, self.pid, "Lyra")
        self.assertEqual(subjects.usable_for_scene(self.p, self.scene, 8), [])
        with self.assertRaises(KeyError):
            subjects.link(self.p, self.pid, "Nobody", ACTIVE)

    def test_games_and_copyright_coverage(self):
        self.assertTrue(subjects.is_covered("FF"))
        self.assertFalse(subjects.is_covered("AOV"))
        self.assertFalse(subjects.is_covered("unknown"))
        self.assertEqual(self.p.project(self.pid)["game"], "FF")  # Free Fire by default
        self.p.set_game(self.pid, "AOV")
        self.assertEqual(self.p.project(self.pid)["game"], "AOV")

    def test_mock_library_is_deterministic_and_validates_the_name(self):
        lib = MockSubjectLibrary()
        a, b = lib.upload("x.png", "FF_Lyra"), lib.upload("x.png", "FF_Lyra")
        self.assertEqual(a["asset_id"], b["asset_id"])
        self.assertTrue(is_active(a))
        with self.assertRaises(ProviderError):
            lib.upload("x.png", " ")


class RunnerSubjectTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
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
        subjects.link(self.p, self.pid, "Lyra", ACTIVE)

    def run_once(self, model, use):
        self.p.set_video_model(self.pid, model)
        self.p.set_use_subjects(self.pid, use)
        provider = MockVideoProvider()
        self.p.create_job(self.scene, "video_gen")
        VideoRunner(self.p, provider, self.data).submit_pending(self.pid)
        return list(provider._tasks.values())[-1]["subjects"]

    def test_subjects_are_sent_only_for_seedance_and_only_when_switched_on(self):
        self.assertEqual(self.run_once("seedance", False), [])
        self.assertEqual(self.run_once("kling", True), [])
        self.assertEqual(self.run_once("seedance", True), [{"name": "Lyra", "uri": "asset://asset-A"}])
        self.assertEqual(self.run_once("seedance-2.5", True), [{"name": "Lyra", "uri": "asset://asset-A"}])


if __name__ == "__main__":
    unittest.main()
