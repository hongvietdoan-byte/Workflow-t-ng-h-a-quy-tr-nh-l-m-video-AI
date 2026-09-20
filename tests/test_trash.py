import os
import tempfile
import time
import unittest

from core import trash
from core.db import connect
from core.llm_io import approve_motion_prompt, store_motion_prompts
from core.pipeline import Pipeline
from core.providers import MockVideoProvider
from core.runner import VideoRunner

GOOD = {"character": 0.95, "hands_face": 0.9, "composition": 0.9, "mood": 0.9}
LOW = {"character": 0.3, "hands_face": 0.4, "composition": 0.3, "mood": 0.4}      # mean 0.35
MIDDLE = {"character": 0.6, "hands_face": 0.6, "composition": 0.6, "mood": 0.6}    # mean 0.60


def write(path, content=b"x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return path


class TrashFilesTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()

    def test_move_list_restore_roundtrip_in_separate_image_and_video_folders(self):
        img = write(os.path.join(self.data, "1", "images", "job_5.png"))
        vid = write(os.path.join(self.data, "1", "videos", "03.mp4"))
        ti = trash.move_to_trash(img, self.data, 1, "images", "bị loại", 5, 2)
        tv = trash.move_to_trash(vid, self.data, 1, "videos", "đã xóa", 9, 3)
        self.assertFalse(os.path.exists(img) or os.path.exists(vid))
        self.assertIn(os.path.join("trash", "images"), ti)
        self.assertIn(os.path.join("trash", "videos"), tv)
        (item,) = trash.items(self.data, 1, "images")
        self.assertEqual((item["reason"], item["job_id"], item["scene_idx"], item["original"]),
                         ("bị loại", 5, 2, "images/job_5.png"))
        self.assertEqual(len(trash.items(self.data, 1, "videos")), 1)
        self.assertEqual(trash.find_for_job(self.data, 1, "images", 5), ti)
        self.assertEqual(trash.restore(self.data, 1, "images", item["file"]), img)
        self.assertTrue(os.path.exists(img))
        self.assertEqual(trash.items(self.data, 1, "images"), [])

    def test_missing_file_is_ignored_and_names_do_not_collide(self):
        self.assertIsNone(trash.move_to_trash(os.path.join(self.data, "nope.png"), self.data, 1, "images", "x"))
        now = 1_800_000_000.0
        for _ in range(2):
            p = write(os.path.join(self.data, "1", "videos", "01.mp4"))
            trash.move_to_trash(p, self.data, 1, "videos", "thay", now=now)
        self.assertEqual(len({i["file"] for i in trash.items(self.data, 1, "videos", now=now)}), 2)

    def test_restore_refuses_to_overwrite(self):
        p = write(os.path.join(self.data, "1", "videos", "01.mp4"), b"old")
        trash.move_to_trash(p, self.data, 1, "videos", "x")
        write(p, b"new")
        (item,) = trash.items(self.data, 1, "videos")
        with self.assertRaises(ValueError):
            trash.restore(self.data, 1, "videos", item["file"])
        self.assertEqual(open(p, "rb").read(), b"new")

    def test_purge_removes_only_entries_older_than_30_days_across_projects(self):
        now = time.time()
        old = write(os.path.join(self.data, "1", "images", "job_1.png"))
        recent = write(os.path.join(self.data, "2", "videos", "01.mp4"))
        trash.move_to_trash(old, self.data, 1, "images", "x", now=now - 31 * 86400)
        trash.move_to_trash(recent, self.data, 2, "videos", "x", now=now - 29 * 86400)
        self.assertEqual(trash.purge_expired(self.data, now=now), 1)
        self.assertEqual(trash.items(self.data, 1, "images"), [])
        (kept,) = trash.items(self.data, 2, "videos", now=now)
        self.assertTrue(os.path.exists(kept["path"]))
        self.assertEqual(kept["days_left"], 1)
        self.assertEqual(trash.purge_expired(self.data, now=now), 0)
        self.assertEqual(trash.purge_expired(os.path.join(self.data, "missing")), 0)

    def test_retention_can_be_configured(self):
        os.environ["TRASH_DAYS"] = "7"
        try:
            self.assertEqual(trash.retention_days(), 7)
        finally:
            os.environ.pop("TRASH_DAYS")
        self.assertEqual(trash.retention_days(), 30)


class SweepAndRunnerTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t", "human_qc", 0.85, 2)
        self.scene = self.p.create_scene(self.pid, 1, "S1")

    def image_job(self):
        job = self.p.create_job(self.scene)
        self.p.start(job)
        self.p.succeed(job)
        write(os.path.join(self.data, str(self.pid), "images", f"job_{job}.png"))
        return job

    def test_rejected_image_goes_to_trash_once_and_restore_sticks(self):
        job = self.image_job()
        self.p.reject(job, "user", "sai áo")
        self.assertEqual(trash.sweep_rejected(self.p, self.data, self.pid), 1)
        self.assertEqual(trash.sweep_rejected(self.p, self.data, self.pid), 0)
        (item,) = trash.items(self.data, self.pid, "images")
        trash.restore(self.data, self.pid, "images", item["file"])
        self.assertEqual(trash.sweep_rejected(self.p, self.data, self.pid), 0)  # not thrown away again
        self.assertTrue(os.path.exists(os.path.join(self.data, str(self.pid), "images", f"job_{job}.png")))

    def test_approved_images_are_never_swept(self):
        job = self.image_job()
        self.p.approve(job)
        self.assertEqual(trash.sweep_rejected(self.p, self.data, self.pid), 0)

    def test_plain_delete_does_not_queue_a_new_job(self):
        job = self.image_job()
        self.p.reject(job, "user", "đã xóa", respawn=False)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) c FROM jobs WHERE parent_job_id=?", (job,)).fetchone()["c"], 0)
        job2 = self.image_job()
        self.p.reject(job2, "user", "sai")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) c FROM jobs WHERE parent_job_id=?", (job2,)).fetchone()["c"], 1)

    def test_regenerated_video_moves_the_old_clip_to_the_trash(self):
        img = self.p.create_job(self.scene)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": "push in"}]})
        approve_motion_prompt(self.p, self.scene)
        clip = write(os.path.join(self.data, str(self.pid), "videos", "01.mp4"), b"OLD CLIP")
        job = self.p.create_job(self.scene, "video_gen")
        VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data).run(self.pid, interval=0, sleep=lambda s: None)
        self.assertNotEqual(open(clip, "rb").read(), b"OLD CLIP")
        (item,) = trash.items(self.data, self.pid, "videos")
        self.assertEqual(open(item["path"], "rb").read(), b"OLD CLIP")
        self.assertEqual(item["reason"], "bị thay bằng bản gen lại")
        self.assertEqual(self.p.state(job).value, "succeeded")


class QcRejectFloorTests(unittest.TestCase):
    def make(self, mode):
        p = Pipeline(connect())
        pid = p.create_project("t", mode, 0.85, 3)
        job = p.create_job(p.create_scene(pid, 1, "S1"))
        p.start(job)
        p.succeed(job)
        return p, pid, job

    def test_default_floor_is_50_for_new_projects(self):
        p, pid, _ = self.make("human_qc")
        self.assertEqual(p.project(pid)["qc_reject_floor"], 0.5)

    def test_low_score_is_rejected_and_requeued_even_in_human_qc(self):
        p, pid, job = self.make("human_qc")
        self.assertEqual(p.apply_qc(job, LOW, issues="tay 6 ngón"), "rejected")
        self.assertEqual(p.state(job).value, "rejected")
        retry = p.conn.execute("SELECT state, retry_reason FROM jobs WHERE parent_job_id=?", (job,)).fetchone()
        self.assertEqual(retry["state"], "queued")
        self.assertIn("tay 6 ngón", retry["retry_reason"])
        self.assertEqual(p.conn.execute("SELECT DISTINCT auto_decision FROM qc_results").fetchone()[0], "fail")

    def test_passing_score_still_waits_for_a_human_in_human_qc(self):
        p, _, job = self.make("human_qc")
        self.assertEqual(p.apply_qc(job, GOOD), "pending_review")
        self.assertEqual(p.state(job).value, "pending_review")

    def test_middling_score_waits_for_a_human_when_above_the_floor(self):
        p, _, job = self.make("human_qc")
        self.assertEqual(p.apply_qc(job, MIDDLE), "pending_review")

    def test_floor_can_be_raised_to_70_or_switched_off(self):
        p, pid, job = self.make("human_qc")
        p.set_reject_floor(pid, 0.7)
        self.assertEqual(p.apply_qc(job, MIDDLE), "rejected")  # 0.60 < 0.70
        p2, pid2, job2 = self.make("human_qc")
        p2.set_reject_floor(pid2, None)
        self.assertEqual(p2.apply_qc(job2, LOW), "pending_review")

    def test_auto_mode_floor_beats_review_zone(self):
        p, pid, job = self.make("auto")
        p.set_review_floor(pid, 0.2)
        self.assertEqual(p.apply_qc(job, LOW), "rejected")  # 0.35 < reject floor 0.5, though inside the review zone

    def test_repeated_low_scores_escalate_after_max_retries(self):
        p, pid, job = self.make("human_qc")
        p.conn.execute("UPDATE projects SET max_retry_count=0 WHERE id=?", (pid,))
        p.conn.commit()
        self.assertEqual(p.apply_qc(job, LOW), "escalated")


if __name__ == "__main__":
    unittest.main()
