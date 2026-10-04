"""The whole pipeline run step after step (mock providers), plus the awkward sequences found while checking it."""
import json
import os
import tempfile
import unittest

from core import final_cut, llm_io, llm_runner, regen, script_parser, subjects, trash
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider, MockVideoProvider
from core.runner import ImageRunner, VideoRunner
from core.states import InvalidTransition

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "samples", "script_demo_1.docx")


def no_sleep(_):
    return None


class FullSequenceTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("seq", "human_qc", 0.85, 2)
        self.llm = llm_runner.MockLlm()

    def load_script(self):
        paragraphs = script_parser.read_docx_paragraphs(SAMPLE)
        parsed = script_parser.split_scenes(paragraphs)
        script_parser.import_scenes(self.p, self.pid, parsed, full_text="\n\n".join(paragraphs))
        return parsed

    def run_images(self):
        ImageRunner(self.p, MockImageProvider(), self.data).run(self.pid, interval=0, sleep=no_sleep)

    def test_script_to_final_clips_step_by_step(self):
        parsed = self.load_script()
        self.assertEqual(len(parsed), 6)
        self.assertIn(parsed[0].heading, self.p.project(self.pid)["script_text"])  # the whole script is kept
        # 1. Director + lock
        llm_runner.run_director(self.p, self.pid, self.llm)
        self.assertEqual(llm_io.lock_character_bible(self.p, self.pid), 6)
        # 2. images: one job per ready scene, all reviewed by a human (human_qc never auto-approves)
        for r in self.p.conn.execute("SELECT id FROM scenes WHERE state='ready'").fetchall():
            self.p.create_job(r["id"], "image_gen")
        self.run_images()
        decisions = llm_runner.run_qc_batch(self.p, self.pid, self.llm, self.data)["decisions"]
        self.assertEqual(decisions, {"pending_review": 6})
        for j in self.p.conn.execute("SELECT id FROM jobs WHERE state='pending_review'").fetchall():
            self.p.approve(j["id"], "user")
        # 3. motion prompts: only for scenes with an approved image, then approved by the user
        self.assertEqual(llm_runner.run_motion(self.p, self.pid, self.llm, self.data)["scenes"], 6)
        for r in self.p.conn.execute("SELECT scene_id FROM motion_prompts").fetchall():
            llm_io.approve_motion_prompt(self.p, r["scene_id"])
        ready = llm_io.ready_for_video(self.p, self.pid)
        self.assertEqual(len(ready), 6)
        # 4. videos
        for r in ready:
            self.p.create_job(r["scene_id"], "video_gen")
        VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data).run(self.pid, interval=0, sleep=no_sleep)
        states = {r["state"] for r in self.p.conn.execute("SELECT state FROM jobs WHERE type='video_gen'")}
        self.assertEqual(states, {"succeeded"})
        clips = [c for c in final_cut.collect_clips(self.p, self.data, self.pid) if c["path"]]
        self.assertEqual([c["idx"] for c in clips], [1, 2, 3, 4, 5, 6])
        # 5. one clip is not good: regenerate it (old take goes to the trash, the others are untouched)
        job = self.p.conn.execute("SELECT id FROM jobs WHERE type='video_gen' ORDER BY id LIMIT 1").fetchone()["id"]
        new = regen.regenerate_video(self.p, self.data, job)
        VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data).run(self.pid, interval=0, sleep=no_sleep)
        self.assertEqual(self.p.state(new).value, "succeeded")
        self.assertEqual(len(trash.items(self.data, self.pid, "videos")), 1)
        self.assertEqual(len([c for c in final_cut.collect_clips(self.p, self.data, self.pid) if c["path"]]), 6)

    def test_importing_twice_is_refused_without_touching_the_first_import(self):
        self.load_script()
        with self.assertRaises(ValueError) as e:
            self.load_script()
        self.assertIn("Làm lại", str(e.exception))                     # the "↺ Làm lại" button (was "Reset")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) c FROM scenes").fetchone()["c"], 6)

    def test_a_script_without_scene_headings_gives_a_clear_message(self):
        with self.assertRaises(ValueError) as e:  # nothing to split at all
            script_parser.import_scenes(self.p, self.pid, script_parser.split_scenes([]))
        self.assertIn("thêm cảnh thủ công", str(e.exception))
        only = script_parser.split_scenes(["chỉ là một đoạn văn, không có tiêu đề cảnh"])
        self.assertEqual([(s.idx, s.heading) for s in only], [(1, "Mở đầu")])  # whole text becomes ONE scene (dashboard warns)
        idx = self.p.add_scene_next(self.pid)  # ...and the user can build the scenes by hand
        self.assertEqual(idx, 1)
        self.assertEqual(self.p.add_scene_next(self.pid), 2)


class DeadEndTests(unittest.TestCase):
    """Sequences that used to leave a scene stuck."""

    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("dead", "human_qc", 0.85, 1)
        self.scene = self.p.create_scene(self.pid, 1, "S1")

    def finished_image(self):
        job = self.p.create_job(self.scene)
        self.p.start(job)
        self.p.succeed(job)
        return job

    def test_escalated_image_scene_can_start_over(self):
        # S14.16: a person's reject is never capped any more — the escalation comes from the automatic (QC) rejects
        job = self.finished_image()
        self.assertEqual(self.p.reject(job, "ai_agent", "sai lần 1"), "rejected")  # max_retry=1: one automatic retry allowed
        retry = self.p.conn.execute("SELECT id FROM jobs WHERE parent_job_id=?", (job,)).fetchone()["id"]
        self.p.start(retry)
        self.p.succeed(retry)
        self.assertEqual(self.p.reject(retry, "ai_agent", "vẫn sai"), "escalated")
        self.assertEqual(self.p.conn.execute("SELECT state FROM scenes").fetchone()["state"], "needs_attention")
        new = self.p.restart_job(retry)
        self.assertEqual((self.p.state(new).value, self.p.job(new)["retry_count"]), ("queued", 0))
        self.assertEqual(self.p.conn.execute("SELECT state FROM scenes").fetchone()["state"], "ready")
        self.assertEqual(self.p.job(retry)["escalated"], 0)
        with self.assertRaises(InvalidTransition):
            self.p.restart_job(new)  # only escalated jobs restart

    def test_escalated_failed_video_no_longer_blocks_a_new_video_job(self):
        v = self.p.create_job(self.scene, "video_gen")
        self.p.start(v)
        self.p.fail(v, "boom")
        v2 = self.p.retry(v, "1st retry")
        self.p.start(v2)
        self.p.fail(v2, "boom again")
        self.assertIsNone(self.p.retry(v2, "no more"))  # exhausted -> escalated
        self.assertEqual(self.p.job(v2)["escalated"], 1)
        new = self.p.restart_job(v2)
        live = self.p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='video_gen'"
                                   " AND state NOT IN ('cancelled','rejected') AND id!=?", (self.scene, new)).fetchall()
        self.assertEqual(live, [])  # the dashboard's "already has a live video job" check passes for the new one only
        self.assertEqual(self.p.state(v2).value, "cancelled")

    def test_an_approved_image_can_be_reopened_with_a_reason(self):
        job = self.finished_image()
        self.p.approve(job, "user")
        self.assertEqual(self.p.reopen_approved(job, "màu áo sai"), "rejected")
        self.assertEqual(self.p.state(job).value, "rejected")
        retry = self.p.conn.execute("SELECT state, retry_reason FROM jobs WHERE parent_job_id=?", (job,)).fetchone()
        self.assertEqual((retry["state"], retry["retry_reason"]), ("queued", "màu áo sai"))
        log = self.p.conn.execute("SELECT reviewer_type, decision FROM review_log WHERE job_id=?", (job,)).fetchall()
        self.assertEqual([(r["reviewer_type"], r["decision"]) for r in log], [("user", "approve"), ("user", "reject")])

    def test_reopen_only_applies_to_approved_images(self):
        job = self.finished_image()
        with self.assertRaises(InvalidTransition):
            self.p.reopen_approved(job)  # not approved yet
        video = self.p.create_job(self.scene, "video_gen")
        with self.assertRaises(ValueError):
            self.p.reopen_approved(video)

    def test_delete_scene_only_when_it_has_no_jobs(self):
        other = self.p.add_scene_next(self.pid)
        self.p.delete_scene(self.pid, other)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) c FROM scenes").fetchone()["c"], 1)
        self.finished_image()
        with self.assertRaises(ValueError):
            self.p.delete_scene(self.pid, 1)
        with self.assertRaises(KeyError):
            self.p.delete_scene(self.pid, 99)


class BibleAndGamesTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("b")

    def test_bible_accepts_creatures_and_props_not_just_people(self):
        llm_io.add_character(self.p, self.pid, "Rồng lửa", "Rồng đỏ cao 5m, vảy như dung nham", "sừng đen")
        llm_io.add_character(self.p, self.pid, "Kiếm rune", "Thanh kiếm dài, khắc rune xanh")
        names = [r["name"] for r in self.p.conn.execute("SELECT name FROM characters ORDER BY id")]
        self.assertEqual(names, ["Rồng lửa", "Kiếm rune"])
        with self.assertRaises(ValueError):
            llm_io.add_character(self.p, self.pid, "Rồng lửa", "trùng tên")
        with self.assertRaises(ValueError):
            llm_io.add_character(self.p, self.pid, " ", "x")
        subjects.link(self.p, self.pid, "Rồng lửa", {"asset_id": "asset-1", "asset_uri": "asset://asset-1",
                                                       "provider_status": "active", "name": "MV_Rong"})  # subjects work for them too

    def test_games_come_from_a_file_and_can_be_extended(self):
        original = subjects.GAMES_PATH
        subjects.GAMES_PATH = os.path.join(tempfile.mkdtemp(), "games.json")
        try:
            with open(subjects.GAMES_PATH, "w", encoding="utf-8") as f:
                json.dump({"games": [{"key": "FF", "label": "Free Fire", "covered": True},
                                     {"key": "OTHER", "label": "Khác", "covered": False}]}, f)
            self.assertEqual(list(subjects.games()), ["FF", "OTHER"])
            subjects.add_game("mv ca sĩ", "MV ca sĩ", covered=False)
            self.assertEqual(list(subjects.games()), ["FF", "MV_CA_SĨ", "OTHER"])  # 'other' stays last
            self.assertFalse(subjects.is_covered("MV_CA_SĨ"))
            self.assertTrue(subjects.is_covered("FF"))
            with self.assertRaises(ValueError):
                subjects.add_game("FF", "again")
            os.remove(subjects.GAMES_PATH)
            self.assertIn("FF", subjects.games())  # missing file -> sensible defaults
        finally:
            subjects.GAMES_PATH = original

    def test_shipped_games_file_marks_only_free_fire_as_covered(self):
        catalog = subjects.games()
        self.assertTrue(catalog["FF"][1])
        self.assertFalse(any(v[1] for k, v in catalog.items() if k != "FF"))


if __name__ == "__main__":
    unittest.main()
