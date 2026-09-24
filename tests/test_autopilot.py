import json
import os
import tempfile
import time
import unittest
from unittest import mock

from core import autopilot, knowledge, llm_io, llm_runner, music, script_parser  # noqa: F401
from core.db import connect
from core.music import MockAudioProvider
from core.pipeline import Pipeline
from core.providers import MockImageProvider, MockVideoProvider
from core.runner import ImageRunner, VideoRunner

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "samples", "script_demo_1.docx")


def fake_render(p, pid, data_dir, music_path):
    out = os.path.join(data_dir, str(pid), "output", "FINAL_VIDEO.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as f:
        f.write(b"FINAL:" + (music_path or "no-music").encode())
    return out


class Setup(unittest.TestCase):
    def build(self, llm=None, video=None, image=None, audio=True, max_retry=2):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("auto", "human_qc", 0.85, max_retry)
        autopilot.set_gates(self.p, self.pid, {"bible": False, "storyboard": False})   # these tests cover the unattended run (the v2 checkpoint: test_v2)
        paragraphs = script_parser.read_docx_paragraphs(SAMPLE)
        script_parser.import_scenes(self.p, self.pid, script_parser.split_scenes(paragraphs), full_text="\n".join(paragraphs))
        self.llm = llm or llm_runner.MockLlm()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())   # the scene breakdown the user reviews
        self.ctx = autopilot.Context(
            self.data, ImageRunner(self.p, image or MockImageProvider(), self.data),
            VideoRunner(self.p, video or MockVideoProvider(polls_to_finish=1), self.data), self.llm,
            MockAudioProvider() if audio else None, fake_render)
        return self.ctx


class FullRunTests(Setup):
    def test_one_approval_then_everything_runs_to_the_final_video(self):
        ctx = self.build()
        self.assertEqual(autopilot.problems(self.p, self.pid, ctx), [])
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.DONE)
        st = autopilot.status(self.p, self.pid)
        self.assertEqual(st["state"], "done")
        self.assertIn("FINAL_VIDEO.mp4", st["note"])
        # every scene went all the way
        for s in self.p.conn.execute("SELECT id FROM scenes"):
            self.assertTrue(self.p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'", (s["id"],)).fetchone())
            self.assertTrue(self.p.conn.execute("SELECT 1 FROM motion_prompts WHERE scene_id=? AND state='approved'", (s["id"],)).fetchone())
            self.assertTrue(self.p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state='succeeded'", (s["id"],)).fetchone())
        # nobody clicked approve: only the AI reviewer decided
        reviewers = {r["reviewer_type"] for r in self.p.conn.execute("SELECT reviewer_type FROM review_log")}
        self.assertEqual(reviewers, {"ai_agent"})
        self.assertEqual(self.p.project(self.pid)["operating_mode"], "human_qc")   # v2: the review mode is given back at the end
        self.assertEqual(len(music.load_drafts(music.project_dirs(self.data, self.pid)[0])), 1)   # one track, not three
        self.assertNotIn("no-music", st["note"] + open(os.path.join(self.data, str(self.pid), "output", "FINAL_VIDEO.mp4")).read())

    def test_without_an_audio_provider_it_renders_without_music(self):
        ctx = self.build(audio=False)
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.DONE)
        self.assertEqual(open(os.path.join(self.data, str(self.pid), "output", "FINAL_VIDEO.mp4")).read(), "FINAL:no-music")

    def test_starting_locks_the_bible_and_nothing_runs_before_the_user_approves(self):
        ctx = self.build()
        self.assertEqual(autopilot.status(self.p, self.pid)["state"], "idle")
        self.assertEqual(autopilot.tick(self.p, self.pid, ctx), "idle")   # a tick does nothing without the approval
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"], 0)
        autopilot.start(self.p, self.pid)
        self.assertTrue(all(r["locked"] for r in self.p.conn.execute("SELECT locked FROM characters")))

    def test_a_tick_is_safe_to_repeat_and_to_resume_after_a_restart(self):
        ctx = self.build()
        autopilot.start(self.p, self.pid)
        for _ in range(3):
            autopilot.tick(self.p, self.pid, ctx)
        # "server restart": brand new context objects, same database
        ctx2 = autopilot.Context(self.data, ImageRunner(self.p, MockImageProvider(), self.data),
                                 VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data), self.llm,
                                 MockAudioProvider(), fake_render)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx2), autopilot.DONE)
        jobs = self.p.conn.execute("SELECT COUNT(*) c FROM jobs WHERE type='image_gen'").fetchone()["c"]
        self.assertEqual(jobs, 6)   # no duplicated image jobs


class SafetyTests(Setup):
    def test_a_scene_that_never_passes_qc_stops_the_run_with_a_clear_note(self):
        class Harsh(llm_runner.MockLlm):
            def complete(self, prompt, images=()):
                if "Đính kèm ảnh cần chấm điểm" in prompt:
                    out = {"criteria": {k: 0.2 for k in ("character", "hands_face", "composition", "mood_lighting", "consistency", "scale", "grounding", "set_match")},
                           "issues": ["tay 6 ngón"]}
                    return llm_runner.LlmReply(json.dumps(out), 10, 5)
                return super().complete(prompt, images)

        ctx = self.build(llm=Harsh(), max_retry=1)
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.ATTENTION)
        note = autopilot.status(self.p, self.pid)["note"]
        self.assertIn("hết số lần thử", note)
        # nothing was rendered and no video credit was spent
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) c FROM jobs WHERE type='video_gen'").fetchone()["c"], 0)

    def test_risk_control_block_is_not_retried_and_asks_for_a_human(self):
        class Blocked(llm_runner.MockLlm):
            def complete(self, prompt, images=()):
                reply = super().complete(prompt, images)
                if "# Cảnh đã có ảnh được duyệt" in prompt:
                    data = json.loads(reply.text.strip("`\njson"))
                    data["scenes"][1]["motion_prompt"] = "Wonder Woman flies over the city"
                    return llm_runner.LlmReply(json.dumps(data), 1, 1)
                return reply

        ctx = self.build(llm=Blocked())
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.ATTENTION)
        self.assertIn("risk control", autopilot.status(self.p, self.pid)["note"])
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) c FROM content_moderation_failures").fetchone()["c"], 1)
        blocked = self.p.conn.execute("SELECT COUNT(*) c FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE s.idx=2 AND j.type='video_gen'").fetchone()["c"]
        self.assertEqual(blocked, 1)   # the blocked scene was submitted once, never blindly retried
        # the other scenes are not thrown away: fix the prompt, resume, finish
        row = self.p.conn.execute("SELECT s.id FROM scenes s WHERE s.idx=2").fetchone()
        job = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='video_gen'", (row["id"],)).fetchone()["id"]
        self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='slow push in' WHERE scene_id=?", (row["id"],))
        self.p.conn.commit()
        self.p.retry(job, "prompt fixed")
        self.p.conn.execute("UPDATE projects SET autopilot_state='running' WHERE id=?", (self.pid,))
        self.p.conn.commit()
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.DONE)

    def test_job_cap_stops_a_run_that_keeps_failing(self):
        class AlwaysFailing(MockImageProvider):
            def status(self, task_id):
                from core.providers import TaskStatus
                return TaskStatus("failed", "server_error", "boom", transient=False)

        ctx = self.build(image=AlwaysFailing(), max_retry=1)
        autopilot.start(self.p, self.pid)
        state = autopilot.run_until_done(self.p, self.pid, ctx, max_ticks=100)
        self.assertIn(state, (autopilot.STOPPED, autopilot.ATTENTION))
        cap = 6 * (1 + 2)
        self.assertLessEqual(self.p.conn.execute("SELECT COUNT(*) c FROM jobs WHERE type='image_gen'").fetchone()["c"], cap)

    def test_pause_and_stop_are_respected(self):
        ctx = self.build()
        autopilot.start(self.p, self.pid)
        self.p.set_paused(self.pid, True)
        autopilot.tick(self.p, self.pid, ctx)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"], 0)
        self.p.set_paused(self.pid, False)
        autopilot.stop(self.p, self.pid)
        self.assertEqual(autopilot.tick(self.p, self.pid, ctx), "stopped")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"], 0)

    def test_render_failure_is_reported_not_swallowed(self):
        ctx = self.build()
        ctx.render = lambda *a: (_ for _ in ()).throw(ValueError("ffmpeg blew up"))
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.ERROR)
        self.assertIn("ffmpeg blew up", autopilot.status(self.p, self.pid)["note"])


class PreconditionTests(Setup):
    def test_problems_lists_what_is_missing(self):
        ctx = self.build()
        many = [f"CẢNH {i}" for i in range(20, 20 + autopilot.MAX_SCENES)]
        for i, title in enumerate(many, start=50):
            self.p.create_scene(self.pid, i, title)
        text = " ".join(autopilot.problems(self.p, self.pid, ctx))
        self.assertIn("clip ngắn", text)                 # too many scenes for a short clip
        self.assertNotIn("prompt ảnh", text.lower())      # the Director phase writes them, it is not a precondition
        empty = Pipeline(connect())
        pid = empty.create_project("empty")
        self.assertIn("Chưa có cảnh", autopilot.problems(empty, pid, ctx)[0])
        self.p.set_paused(self.pid, True)
        self.assertIn("PAUSE", " ".join(autopilot.problems(self.p, self.pid, ctx)))

    def test_default_context_needs_providers_and_a_claude_key(self):
        ctx_env = {k: os.environ.pop(k, None) for k in ("IMAGE_PROVIDER", "VIDEO_PROVIDER", "ANTHROPIC_API_KEY", "LLM_PROVIDER")}
        try:
            self.build()
            with self.assertRaises(ValueError) as e:
                autopilot.default_context(self.p, self.data)
            self.assertIn("IMAGE_PROVIDER", str(e.exception))
            os.environ["IMAGE_PROVIDER"] = os.environ["VIDEO_PROVIDER"] = "mock"
            with self.assertRaises(ValueError) as e:
                autopilot.default_context(self.p, self.data)
            self.assertIn("ANTHROPIC_API_KEY", str(e.exception))
            os.environ["LLM_PROVIDER"] = "mock"
            self.assertIsNotNone(autopilot.default_context(self.p, self.data).llm)
        finally:
            for k in ("IMAGE_PROVIDER", "VIDEO_PROVIDER", "ANTHROPIC_API_KEY", "LLM_PROVIDER"):
                os.environ.pop(k, None)
                if ctx_env[k] is not None:
                    os.environ[k] = ctx_env[k]

    def test_stale_detection(self):
        self.build()
        autopilot.start(self.p, self.pid)
        self.assertFalse(autopilot.is_stale(self.p, self.pid))
        self.p.conn.execute("UPDATE projects SET autopilot_beat=? WHERE id=?", (time.time() - 3600, self.pid))
        self.p.conn.commit()
        self.assertTrue(autopilot.is_stale(self.p, self.pid))


class ThreadTests(unittest.TestCase):
    def test_background_thread_runs_a_project_to_the_end(self):
        tmp = tempfile.mkdtemp()
        db, data = os.path.join(tmp, "m.sqlite"), os.path.join(tmp, "projects")
        p = Pipeline(connect(db))
        pid = p.create_project("thr", "human_qc", 0.85, 2)
        autopilot.set_gates(p, pid, {"bible": False, "storyboard": False})
        paragraphs = script_parser.read_docx_paragraphs(SAMPLE)
        script_parser.import_scenes(p, pid, script_parser.split_scenes(paragraphs))
        llm_runner.run_director(p, pid, llm_runner.MockLlm())

        def factory(pipeline, data_dir):
            return autopilot.Context(data_dir, ImageRunner(pipeline, MockImageProvider(), data_dir),
                                     VideoRunner(pipeline, MockVideoProvider(polls_to_finish=1), data_dir),
                                     llm_runner.MockLlm(), MockAudioProvider(), fake_render)

        manager = autopilot.Manager(db, data, factory, poll_sec=0.01)
        autopilot.start(p, pid)
        self.assertTrue(manager.start(pid))
        self.assertFalse(manager.start(pid) and manager.alive(pid) is False)   # a second start does not double up
        deadline = time.time() + 30
        while time.time() < deadline and autopilot.status(Pipeline(connect(db)), pid)["state"] == "running":
            time.sleep(0.1)
        self.assertEqual(autopilot.status(Pipeline(connect(db)), pid)["state"], "done")

    def test_a_broken_configuration_is_reported_in_the_project_not_lost(self):
        tmp = tempfile.mkdtemp()
        db = os.path.join(tmp, "m.sqlite")
        p = Pipeline(connect(db))
        pid = p.create_project("cfg")

        def factory(pipeline, data_dir):
            raise ValueError("Chưa cấu hình nhà cung cấp")

        autopilot.start(p, pid)
        manager = autopilot.Manager(db, tmp, factory, poll_sec=0.01)
        manager.start(pid)
        deadline = time.time() + 10
        while time.time() < deadline and autopilot.status(Pipeline(connect(db)), pid)["state"] == "running":
            time.sleep(0.05)
        st = autopilot.status(Pipeline(connect(db)), pid)
        self.assertEqual(st["state"], "error")
        self.assertIn("Chưa cấu hình", st["note"])


if __name__ == "__main__":
    unittest.main()


class PrevizInAutopilotTests(Setup):
    """The automatic run lays the shots out before the pictures (so they follow the layouts) and never stops because of it."""

    def place(self):
        from PIL import Image
        from core import assets
        os.environ["ASSET_DIR"] = os.path.join(self.data, "assets")
        self.addCleanup(os.environ.pop, "ASSET_DIR", None)
        loc = assets.create(self.p.conn, "FF", "location", "Đảo Quân Sự", "", "", None, "x")
        path = os.path.join(self.data, "bg.png")
        Image.new("RGB", (320, 180), (120, 150, 110)).save(path)
        assets.add_image(self.p.conn, loc, "bg.png", open(path, "rb").read())
        assets.attach(self.p.conn, self.pid, loc)
        first = self.p.conn.execute("SELECT idx FROM scenes WHERE project_id=? ORDER BY idx LIMIT 1", (self.pid,)).fetchone()["idx"]
        llm_io.update_scene(self.p, self.pid, first, {"location_asset": loc})
        return first

    @mock.patch.dict(os.environ, {"FEATURE_LAYOUT_TO_MODEL": "1"})   # mechanism test; off by default until a real test (core/features.py)
    def test_the_run_lays_out_the_scene_with_a_background_and_its_picture_follows_the_layout(self):
        image = MockImageProvider()
        self.build(image=image)
        first = self.place()
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, self.ctx), autopilot.DONE)
        layout = os.path.join(self.data, str(self.pid), "layouts", f"S{first:02d}.png")
        self.assertTrue(os.path.exists(layout))
        self.assertIn(layout, [refs[0] for refs in image.references.values() if refs])
        self.assertTrue(os.path.exists(os.path.join(self.data, str(self.pid), "layouts", ".autopilot_done")))   # only once per project

    def test_claude_failing_on_the_layout_does_not_stop_the_run(self):
        class NoLayout(llm_runner.MockLlm):
            def complete(self, prompt, images=()):
                if prompt.startswith("# Phân tích ảnh nền"):
                    raise llm_runner.LlmError("monthly spend limit", code="quota")
                return super().complete(prompt, images)
        self.build(llm=NoLayout())
        self.place()
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, self.ctx), autopilot.DONE)
        self.assertTrue(self.p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='previz_skipped'").fetchone()[0])
