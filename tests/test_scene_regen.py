import json
import os
import tempfile
import unittest
from unittest import mock

from core import final_cut, ffmpeg_studio, regen, trash
from core.adapters.clipai import ClipAIVideoProvider
from core.db import connect
from core.llm_io import (SchemaError, approve_motion_prompt, store_motion_prompts, store_scene_analysis,
                         update_scene)
from core.pipeline import Pipeline
from core.preflight import load_blocklist, record_failure, risk_notes
from core.providers import MockVideoProvider, ProviderError
from core.runner import VideoRunner
from tests.test_adapters import TOKEN, FakeTransport, ctx_of, ok
from tests.test_llm_io_preflight import ANALYSIS


def write(path, content=b"x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return path


class SceneEditTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.p.create_scene(self.pid, 1, "CẢNH 1")
        store_scene_analysis(self.p, self.pid, ANALYSIS)

    def data(self):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE idx=1").fetchone()["data"])

    def test_edit_spec_and_script_text_keeps_other_fields(self):
        update_scene(self.p, self.pid, 1, {"mood": "  căng thẳng ", "characters": ["Lyra", "Nữ chiến binh Amazon"],
                                           "image_prompt": "dark forest at night"}, text="Đoạn mới")
        d = self.data()
        self.assertEqual((d["mood"], d["image_prompt"], d["text"]), ("căng thẳng", "dark forest at night", "Đoạn mới"))
        self.assertEqual(d["characters"], ["Lyra", "Nữ chiến binh Amazon"])
        self.assertEqual(d["lighting"], "ánh trăng")  # untouched

    def test_validation(self):
        with self.assertRaises(SchemaError):
            update_scene(self.p, self.pid, 1, {"characters": ["Ai đó"]})
        with self.assertRaises(SchemaError):
            update_scene(self.p, self.pid, 1, {"image_prompt": "   "})
        with self.assertRaises(SchemaError):
            update_scene(self.p, self.pid, 1, {"mood": 5})
        with self.assertRaises(KeyError):
            update_scene(self.p, self.pid, 9, {"mood": "x"})
        self.assertEqual(self.data()["mood"], "u ám")  # nothing half-applied


class RegenerateVideoTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t", max_retry=1)
        self.scene = self.p.create_scene(self.pid, 1, "S1")
        img = self.p.create_job(self.scene)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "push in"}]})
        approve_motion_prompt(self.p, self.scene)

    def finished_video(self):
        job = self.p.create_job(self.scene, "video_gen")
        self.p.start(job)
        self.p.succeed(job)
        path = write(os.path.join(self.data, str(self.pid), "videos", "01.mp4"), b"TAKE-1")
        self.p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (path, job))
        self.p.conn.commit()
        return job, path

    def test_old_clip_goes_to_trash_and_a_fresh_job_is_queued(self):
        job, path = self.finished_video()
        new = regen.regenerate_video(self.p, self.data, job)
        self.assertFalse(os.path.exists(path))
        (item,) = trash.items(self.data, self.pid, "videos")
        self.assertEqual((open(item["path"], "rb").read(), item["reason"]), (b"TAKE-1", "gen lại video"))
        self.assertEqual(self.p.state(job).value, "rejected")
        self.assertEqual((self.p.state(new).value, self.p.job(new)["retry_count"]), ("queued", 0))

    def test_can_regenerate_more_times_than_max_retry(self):
        job, _ = self.finished_video()
        for _ in range(3):  # max_retry is 1: a user-requested new take must not be capped by it
            new = regen.regenerate_video(self.p, self.data, job)
            VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data).run(self.pid, 0, sleep=lambda s: None)
            self.assertEqual(self.p.state(new).value, "succeeded")
            job = new
        self.assertEqual(len(trash.items(self.data, self.pid, "videos")), 3)

    def test_only_finished_video_jobs(self):
        queued = self.p.create_job(self.scene, "video_gen")
        with self.assertRaises(Exception):
            regen.regenerate_video(self.p, self.data, queued)
        with self.assertRaises(ValueError):
            regen.regenerate_video(self.p, self.data, self.p.conn.execute(
                "SELECT id FROM jobs WHERE type='image_gen'").fetchone()["id"])


class PreviewWithMusicTests(unittest.TestCase):
    def test_uses_existing_clips_in_scene_order_with_the_music(self):
        data = tempfile.mkdtemp()
        p = Pipeline(connect())
        pid = p.create_project("t")
        for i in (1, 2, 3):
            p.create_scene(pid, i, f"S{i}")
        write(os.path.join(data, str(pid), "videos", "01.mp4"))
        write(os.path.join(data, str(pid), "videos", "03.mp4"))
        calls = []
        with mock.patch.object(ffmpeg_studio, "probe_duration", return_value=4.0), \
                mock.patch.object(ffmpeg_studio, "render_final", side_effect=lambda *a: calls.append(a) or a[1]):
            out = final_cut.preview_with_music(p, data, pid, "m.mp3", os.path.join(data, "prev.mp4"), 0.5)
        clips, output, durations, transition, fade, music, volume = calls[0]
        self.assertEqual([os.path.basename(c) for c in clips], ["01.mp4", "03.mp4"])
        self.assertEqual((durations, transition, music, volume), ([4.0, 4.0], "cut", "m.mp3", 0.5))
        self.assertEqual(out, os.path.join(data, "prev.mp4"))

    def test_no_clips_is_a_clear_error(self):
        p = Pipeline(connect())
        pid = p.create_project("t")
        with self.assertRaises(ValueError):
            final_cut.preview_with_music(p, tempfile.mkdtemp(), pid, "m.mp3", "o.mp4")


class RiskNoteTests(unittest.TestCase):
    def test_collects_ip_warnings_and_moderation_blocks_with_scene(self):
        p = Pipeline(connect())
        pid = p.create_project("t")
        scene = p.create_scene(pid, 4, "S4")
        store_scene_analysis(p, pid, {**ANALYSIS, "scenes": [{**ANALYSIS["scenes"][0], "idx": 4}]})
        job = p.create_job(scene, "video_gen")
        record_failure(p.conn, job, "clipai", "Failure to pass the risk control system")
        notes = risk_notes(p.conn, pid, load_blocklist())
        kinds = {n["kind"] for n in notes}
        self.assertEqual(kinds, {"ip", "moderation"})
        moderation = next(n for n in notes if n["kind"] == "moderation")
        self.assertEqual((moderation["scene"], moderation["title"]), (4, "Cảnh 4 bị chặn (clipai)"))
        self.assertIn("risk control", moderation["detail"])


class GeneratedAudioOptionTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.p = ClipAIVideoProvider(TOKEN, "https://clipai.example", self.t)
        self.image = write(os.path.join(tempfile.mkdtemp(), "i.png"), b"\x89PNG-fake")

    def test_default_is_silent_for_both_families(self):
        self.t.on("POST", "*", ok({"tasks": [{"task_id": "T", "task_status": "submitted"}]}))
        self.p.submit(self.image, "x", None, 5)
        self.p.submit(self.image, "x", None, 5, "seedance")
        omni, seed = ctx_of(self.t.calls[0]), ctx_of(self.t.calls[1])
        self.assertEqual(omni["sound"], "off")
        self.assertFalse(seed["generate_audio"])

    def test_with_audio_turns_on_kling_sound_and_seedance_generate_audio(self):
        self.t.on("POST", "*", ok({"tasks": [{"task_id": "T", "task_status": "submitted"}]}))
        self.p.submit(self.image, "x", None, 5, "kling", True)
        self.p.submit(self.image, "x", None, 5, "seedance-2.5", True)
        self.assertEqual(ctx_of(self.t.calls[0])["sound"], "on")
        self.assertTrue(ctx_of(self.t.calls[1])["generate_audio"])

    def test_kling_o1_cannot_do_sound(self):
        with self.assertRaises(ProviderError) as e:
            self.p.submit(self.image, "x", None, 5, "kling-o1", True)
        self.assertEqual(e.exception.code, "unsupported_option")
        self.assertEqual(self.t.calls, [])  # nothing sent, nothing billed

    def test_runner_passes_the_flag_only_when_the_project_asks(self):
        data = tempfile.mkdtemp()
        db = Pipeline(connect())
        pid = db.create_project("t")
        scene = db.create_scene(pid, 1, "S1")
        img = db.create_job(scene)
        db.start(img)
        db.succeed(img)
        db.approve(img)
        store_motion_prompts(db, pid, {"scenes": [{"idx": 1, "motion_prompt": "push in"}]})
        approve_motion_prompt(db, scene)
        write(os.path.join(data, str(pid), "images", f"job_{img}.png"))
        db.create_job(scene, "video_gen")
        provider = MockVideoProvider()
        runner = VideoRunner(db, provider, data)
        runner.submit_pending(pid)
        self.assertFalse(provider._tasks["mock-1"]["with_audio"])
        db.set_video_audio(pid, True)
        db.create_job(scene, "video_gen")
        runner.submit_pending(pid)
        self.assertTrue(provider._tasks["mock-2"]["with_audio"])


if __name__ == "__main__":
    unittest.main()
