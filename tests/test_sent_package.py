"""K1a "Lưu gói gửi" (docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md): every send path writes what REALLY left — byte for byte — on
the job (jobs.sent_package / end_frames.sent_package). A ledger, never a gate: a failure is said (diag warn) and the send stands.
Provider doubles only, temporary databases, nothing under data/."""
import functools
import hashlib
import json
import os
import pathlib
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from core import end_frames, llm_io, llm_runner, quality_tier, sent_package
from core.adapters.clipai import ClipAIVideoProvider
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider, MockVideoProvider
from core.runner import ImageRunner, VideoRunner


def spy(provider, name="submit"):
    """Wrap provider.<name> (signature kept via functools.wraps) and remember every call exactly as made."""
    orig = getattr(provider, name)
    calls = []

    @functools.wraps(orig)
    def wrapper(*a, **k):
        calls.append((a, dict(k)))
        return orig(*a, **k)
    setattr(provider, name, wrapper)
    return calls


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def package(conn, job_id, table="jobs"):
    raw = conn.execute(f"SELECT sent_package FROM {table} WHERE id=?", (job_id,)).fetchone()[0]
    return json.loads(raw) if raw else None


def diags(conn, code="sent_package"):
    return conn.execute("SELECT severity, message FROM diag_events WHERE code=?", (code,)).fetchall()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect(os.path.join(self.tmp, "t.db")))
        self.dir = os.path.join(self.tmp, "projects")
        os.makedirs(self.dir)
        self.pid = self.p.create_project("k1a", max_retry=2)

    def tearDown(self):
        self.p.conn.close()

    def file(self, name, body=b"picture"):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as f:
            f.write(body)
        return path


class ImagePathTests(Base):
    def setUp(self):
        super().setUp()
        self.scene = self.p.create_scene(self.pid, 1, "S1")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                            (json.dumps({"image_prompt": "sương mù — Lyra đứng ở bậc thang “giữa”"}, ensure_ascii=False), self.scene))
        self.p.conn.commit()

    def test_image_package_is_the_prompt_really_sent(self):
        job = self.p.create_job(self.scene)
        prov = MockImageProvider()
        calls = spy(prov)
        ImageRunner(self.p, prov, self.dir).submit_pending(self.pid)
        self.assertEqual(len(calls), 1)
        (args, kwargs), pkg = calls[0], package(self.p.conn, job)
        self.assertEqual(pkg["prompt"].encode("utf-8"), args[0].encode("utf-8"))          # byte for byte
        self.assertEqual((pkg["v"], pkg["provider"], pkg["external_id"]), (1, "mock-image", self.p.job(job)["external_id"]))
        self.assertEqual(pkg["params"], {k: v for k, v in kwargs.items()})
        self.assertTrue(pkg["at"])

    def test_image_refs_carry_role_label_relative_path_and_sha(self):
        job = self.p.create_job(self.scene)
        good = self.file("kelly.png", b"kelly")
        prov = MockImageProvider()
        calls = spy(prov)
        r = ImageRunner(self.p, prov, self.dir)
        r._sent = {job: [{"label": "KELLY", "role": "character", "file": "kelly.png"}]}
        with mock.patch.object(r, "_submit_args", return_value=("Image 1 is KELLY. Scene: x", [good])):
            r.submit_pending(self.pid)
        pkg = package(self.p.conn, job)
        self.assertEqual(calls[0][0], ("Image 1 is KELLY. Scene: x", [good]))
        self.assertEqual(len(pkg["refs"]), 1)
        ref = pkg["refs"][0]
        self.assertEqual((ref["label"], ref["role"], ref["file"], ref["sha256"]), ("KELLY", "character", "kelly.png", sha(good)))
        self.assertEqual(ref["path"], sent_package.rel_path(good))
        self.assertNotIn("\\", ref["path"])

    def test_unreadable_picture_sha_null_said_and_still_sent(self):
        job = self.p.create_job(self.scene)
        missing = os.path.join(self.tmp, "gone.png")
        prov = MockImageProvider()
        calls = spy(prov)
        r = ImageRunner(self.p, prov, self.dir)
        with mock.patch.object(r, "_submit_args", return_value=("p", [missing])):
            r.submit_pending(self.pid)
        self.assertEqual(len(calls), 1)                                                  # sent anyway
        self.assertEqual(self.p.job(job)["state"], "running")
        self.assertIsNone(package(self.p.conn, job)["refs"][0]["sha256"])
        said = diags(self.p.conn)
        self.assertTrue(said and said[0]["severity"] == "warn" and "gone.png" in said[0]["message"])


class VideoPathTests(Base):
    def video_job(self, prompt="slow push-in — Kenta “bước tới”"):
        scene = self.p.create_scene(self.pid, 1, "S1")
        img = self.p.create_job(scene)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": 1, "motion_prompt": prompt}]})
        llm_io.approve_motion_prompt(self.p, scene)
        return self.p.create_job(scene, "video_gen")

    def send(self, prov):
        calls = spy(prov)
        VideoRunner(self.p, prov, self.dir, max_concurrent=2).submit_pending(self.pid)
        return calls

    def test_video_package_matches_args_and_kwargs(self):
        job = self.video_job()
        calls = self.send(MockVideoProvider())
        self.assertEqual(len(calls), 1)
        (args, kwargs), pkg = calls[0], package(self.p.conn, job)
        self.assertEqual(pkg["prompt"].encode("utf-8"), args[1].encode("utf-8"))
        self.assertEqual(pkg["negative"], args[2])
        self.assertEqual(pkg["params"]["duration_sec"], args[3])
        self.assertEqual(pkg["model"], args[4])
        self.assertEqual(pkg["refs"][0]["param"], "image_path")
        self.assertEqual(pkg["refs"][0]["path"], sent_package.rel_path(args[0]))
        for k, v in kwargs.items():
            self.assertEqual(pkg["params"][k], v)
        self.assertEqual(pkg["external_id"], self.p.job(job)["external_id"])

    def test_package_does_not_change_the_call(self):
        """(b) the provider gets the same call whether the package is written or fails to build."""
        self.video_job()
        first = self.send(MockVideoProvider())
        self.p.conn.execute("UPDATE jobs SET state='queued', external_id=NULL WHERE type='video_gen'")
        self.p.conn.commit()
        with mock.patch("core.sent_package.build", side_effect=RuntimeError("boom")):
            second = self.send(MockVideoProvider())
        self.assertEqual(first, second)

    def test_package_failure_never_blocks_the_send(self):
        """(c) build blows up → sent anyway, task id kept, a warn diag, no package."""
        job = self.video_job()
        with mock.patch("core.sent_package.build", side_effect=RuntimeError("boom")):
            calls = self.send(MockVideoProvider())
        self.assertEqual(len(calls), 1)
        row = self.p.job(job)
        self.assertEqual((row["state"], row["external_id"]), ("running", "mock-1"))
        self.assertIsNone(package(self.p.conn, job))
        said = diags(self.p.conn)
        self.assertTrue(said and said[0]["severity"] == "warn" and "boom" in said[0]["message"])

    def test_package_guard_outside_safe_build_keeps_the_task_id(self):
        job = self.video_job()
        with mock.patch("core.sent_package.safe_build", side_effect=sqlite3.OperationalError("locked")):
            calls = self.send(MockVideoProvider())
        self.assertEqual(len(calls), 1)
        self.assertEqual((self.p.job(job)["state"], self.p.job(job)["external_id"]), ("running", "mock-1"))
        self.assertTrue(any("locked" in d["message"] for d in diags(self.p.conn)))


class FinalFromDraftTests(unittest.TestCase):
    """N1 'nâng từ nháp': submit_final_from_sample sends no prompt — the package says so, and points at the draft's own package."""

    def test_final_from_sample_package(self):
        tmp = tempfile.mkdtemp()
        p = Pipeline(connect(os.path.join(tmp, "t.db")))
        pid = p.create_project("N1")
        s1 = p.create_scene(pid, 1, "Shot 1")
        img = p.create_job(s1)
        p.start(img)
        p.succeed(img)
        p.approve(img)
        llm_io.store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "she dances", "duration_sec": 4}]})
        llm_io.approve_motion_prompt(p, s1)
        p.conn.execute("UPDATE motion_prompts SET video_model='seedance-2.5' WHERE scene_id=?", (s1,))
        data = {"difficulty": "unknown", "difficulty_why": "test"}
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), s1))
        p.conn.commit()
        from core import lineage
        with mock.patch("core.quality_tier.enabled", return_value=True):
            d = p.create_job(s1, "video_gen")
            mp = p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (s1,)).fetchone()
            p.conn.execute("UPDATE jobs SET input_hash=?, source_job_id=?, model=?, external_id=?, sent_package=? WHERE id=?",
                           (lineage.video_input_hash(mp, None), img, "seedance-2.5", f"seedance:t{d}",
                            json.dumps({"v": 1, "prompt": "she dances — nháp", "refs": []}, ensure_ascii=False), d))
            p.conn.commit()
            p.start(d)
            p.succeed(d)
            p.approve(d, "user")
            f = quality_tier.request_final(p, s1)
            prov = ClipAIVideoProvider("tok", "https://example.invalid", lambda *a, **k: None)
            prov.task_usage = mock.Mock(return_value={"is_draft": True, "draft_expired_at": (time.time() + 3600) * 1000})
            prov.submit_final_from_sample = mock.Mock(return_value="seedance:final")
            prov.submit = mock.Mock(return_value="seedance:resend")
            vr = VideoRunner(p, prov, tmp)
            with mock.patch.object(vr, "_submit_args", return_value=("i.png", "she dances", None, 4, "seedance-2.5")), \
                    mock.patch.object(vr, "_blocked", return_value=None), mock.patch.object(vr, "_stamp", return_value={}), \
                    mock.patch.object(vr, "_over_budget", return_value=None), mock.patch.object(vr, "_wait", return_value=False):
                self.assertEqual(vr._submit_pending(pid), 1)
        prov.submit_final_from_sample.assert_called_once_with(f"seedance:t{d}", resolution="1080p")   # call unchanged
        pkg = package(p.conn, f)
        self.assertEqual(pkg["call"], "submit_final_from_sample")
        self.assertIsNone(pkg["prompt"])                                                  # nothing typed went out
        self.assertEqual(pkg["params"], {"sample_external_id": f"seedance:t{d}", "resolution": "1080p"})
        self.assertEqual((pkg["external_id"], pkg["draft_job_id"], pkg["model"]), ("seedance:final", d, "seedance-2.5"))
        self.assertEqual(pkg["draft_prompt"], "she dances — nháp")
        p.conn.close()


class EndFrameTests(unittest.TestCase):
    def test_end_frame_package_matches_the_call(self):
        from tests.test_v3 import _approve_all_images, kenta_project
        from tests.test_end_frames import _shot_with_end_state
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        sid = _shot_with_end_state(p, pid)
        data = tempfile.mkdtemp()
        _approve_all_images(p, pid, data)
        end_frames.queue(p, pid)
        prov = MockImageProvider()
        calls = spy(prov)
        end_frames.tick(p, pid, prov, data)
        row = end_frames.current(p.conn, sid)
        self.assertEqual(row["state"], "running")
        sent = [c for c in calls if "lies on the ground" in c[0][0]]
        self.assertEqual(len(sent), 1)
        (args, kwargs), pkg = sent[0], json.loads(row["sent_package"])
        self.assertEqual(pkg["prompt"].encode("utf-8"), args[0].encode("utf-8"))
        self.assertEqual([r["path"] for r in pkg["refs"]], [sent_package.rel_path(x) for x in args[1]])
        self.assertEqual(pkg["refs"][0]["sha256"], sha(args[1][0]))                     # the start picture, fingerprinted
        self.assertEqual(pkg["refs"][0]["role"], "previous_scene")
        self.assertEqual((pkg["external_id"], pkg["stage"]), (row["external_id"], "end_frame"))
        self.assertEqual(pkg["params"], kwargs)


class BuildTests(unittest.TestCase):
    def test_not_json_secrets_and_base64_never_break_or_leak(self):
        big = "A" * (sent_package.LONG_TEXT + 1)
        text, warns = sent_package.build(
            lambda prompt, references=None, **kw: None, ("p",),
            {"api_key": "sk-123", "access_token": "t", "plate_key": "pk", "where": pathlib.Path("x/y.png"), "raw": b"\x00\x01",
             "obj": object(), "b64": big, "nested": {"password": "z", "ok": 1}},
            kind="image", provider=object(), external_id=7)
        pkg = json.loads(text)
        self.assertNotIn("sk-123", text)
        self.assertEqual(pkg["redacted"], ["access_token", "api_key"])
        self.assertEqual(pkg["params"]["plate_key"], "pk")
        self.assertEqual(pkg["params"]["where"], "x/y.png")
        self.assertEqual(pkg["params"]["raw"]["bytes"], 2)
        self.assertEqual(pkg["params"]["obj"], "<object>")
        self.assertEqual(pkg["params"]["b64"]["len"], len(big))
        self.assertNotIn(big, text)
        self.assertEqual(pkg["params"]["nested"], {"password": "<redacted>", "ok": 1})
        self.assertEqual((pkg["external_id"], warns), ("7", []))

    def test_safe_build_never_raises(self):
        with mock.patch("core.sent_package._bind", side_effect=ValueError("x")):
            pkg, warns = sent_package.safe_build(print, (), {}, kind="image", provider=None, external_id="e")
        self.assertIsNone(pkg)
        self.assertTrue(warns)


class MigrationTests(unittest.TestCase):
    def test_migration_twice_and_old_database_without_the_column(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "old.db")
        c = connect(path)
        pp = Pipeline(c)
        pid = pp.create_project("old")
        job = pp.create_job(pp.create_scene(pid, 1, "S1"))
        c.execute("UPDATE jobs SET external_id='x-1' WHERE id=?", (job,))
        c.commit()
        c.execute("ALTER TABLE jobs DROP COLUMN sent_package")                            # an old database
        c.execute("ALTER TABLE end_frames DROP COLUMN sent_package")
        c.commit()
        c.close()
        for _ in range(2):                                                                # migrated, then again: no error
            c = connect(path)
            cols = {r["name"] for r in c.execute("PRAGMA table_info(jobs)")}
            self.assertIn("sent_package", cols)
            self.assertIn("sent_package", {r["name"] for r in c.execute("PRAGMA table_info(end_frames)")})
            row = c.execute("SELECT external_id, sent_package FROM jobs").fetchone()
            self.assertEqual((row["external_id"], row["sent_package"]), ("x-1", None))  # old rows kept, nothing invented
            c.close()


if __name__ == "__main__":
    unittest.main()
