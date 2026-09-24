import json
import os
import shutil
import struct
import tempfile
import time
import unittest
import zlib

from core import assets, autoqc, llm_runner
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider
from core.runner import ImageRunner
from core.throttle import THROTTLE


def png(seed):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00" + bytes([seed, 0, 0]))) + chunk(b"IEND", b""))


class FakeQc:
    """Answers every QC request with the same scores and issues; remembers what it was shown."""
    name = "fake-qc"

    def __init__(self, score=0.4, issues=("Kelly must wear the yellow tracksuit",)):
        self.score, self.issues, self.prompts, self.images = score, list(issues), [], []

    def complete(self, prompt, images=()):
        self.prompts.append(prompt)
        self.images.append(list(images))
        criteria = {k: self.score for k in ("character", "hands_face", "composition", "mood_lighting", "consistency", "scale", "grounding", "set_match")}
        return llm_runner.LlmReply(json.dumps({"criteria": criteria, "issues": self.issues}), 10, 5)


class Base(unittest.TestCase):
    def setUp(self):
        THROTTLE.reset()
        autoqc._errors.clear()
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.db = os.path.join(self.dir, "m.sqlite")
        self.data = os.path.join(self.dir, "projects")
        self.p = Pipeline(connect(self.db))
        self.pid = self.p.create_project("qc", "human_qc", 0.85, 2)
        self.provider = MockImageProvider(polls_to_finish=1)
        self.runner = ImageRunner(self.p, self.provider, self.data)

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def scene(self, idx=1, characters=("Kelly",), text="", location=""):
        sid = self.p.create_scene(self.pid, idx, f"s{idx}")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(
            {"image_prompt": "hero on a rooftop", "characters": list(characters), "text": text, "location": location}), sid))
        self.p.conn.commit()
        return sid

    def generated_job(self, sid):
        """A job that has been generated (state 'succeeded', picture on disk)."""
        jid = self.p.create_job(sid, "image_gen")
        self.runner.submit_pending(self.pid)
        self.runner.poll_once(self.pid)
        self.assertEqual(self.p.state(jid).value, "succeeded")
        return jid

    def states(self):
        return [(r["id"], r["state"], r["retry_count"], r["retry_reason"]) for r in
                self.p.conn.execute("SELECT id, state, retry_count, retry_reason FROM jobs ORDER BY id")]


class AutoFixTests(Base):
    def test_a_faulty_picture_is_regenerated_with_the_problems_in_its_prompt(self):
        jid = self.generated_job(self.scene())
        result = llm_runner.run_qc(self.p, jid, FakeQc(0.4), self.data, autofix=True)
        self.assertEqual(result["decision"], "auto_fix")
        first, second = self.states()
        self.assertEqual(first[1], "rejected")
        self.assertEqual((second[1], second[2]), ("queued", 1))
        self.assertIn("Kelly must wear the yellow tracksuit", second[3])              # the QC's words are the retry instruction
        self.runner.submit_pending(self.pid)
        sent = list(self.provider.prompts.values())[-1]
        self.assertIn("Fix: Kelly must wear the yellow tracksuit", sent)                 # ... and reach the image model
        self.assertNotIn("QC 0.40", sent)                                                # W4: no score line in the model's prompt

    def test_a_good_picture_goes_to_the_person_and_so_does_any_picture_when_the_switch_is_off(self):
        jid = self.generated_job(self.scene())
        self.assertEqual(llm_runner.run_qc(self.p, jid, FakeQc(0.95), self.data, autofix=True)["decision"], "pending_review")
        jid2 = self.generated_job(self.scene(2))
        self.assertEqual(llm_runner.run_qc(self.p, jid2, FakeQc(0.7), self.data, autofix=False)["decision"], "pending_review")
        self.assertEqual([s[1] for s in self.states()], ["pending_review", "pending_review"])

    def test_after_the_last_try_the_picture_is_kept_for_the_person_and_flagged(self):
        jid = self.generated_job(self.scene())
        llm_runner.run_qc(self.p, jid, FakeQc(0.4), self.data, autofix=True)          # try 1 (limit is 2)
        self.runner.submit_pending(self.pid)
        self.runner.poll_once(self.pid)
        second = [s for s in self.states() if s[1] == "succeeded"][0][0]
        # the same fault after the fix: F5 stops here (a third paid try with the same problem is not made)
        result = llm_runner.run_qc(self.p, second, FakeQc(0.4), self.data, autofix=True)
        self.assertEqual(result["decision"], "needs_review")
        row = self.p.conn.execute("SELECT state, escalated FROM jobs WHERE id=?", (second,)).fetchone()
        self.assertEqual((row["state"], row["escalated"]), ("pending_review", 1))      # not thrown away: the person decides


class ReferenceTests(Base):
    def test_qc_is_shown_the_reference_pictures_and_told_which_is_whom(self):
        a = assets.create(self.p.conn, "FF", "character", "KELLY", "", "", None, "x")
        assets.add_image(self.p.conn, a, "kelly.png", png(1))
        assets.attach(self.p.conn, self.pid, a)
        self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (self.pid, "Kelly", "Kelly, girl"))
        self.p.conn.commit()
        jid = self.generated_job(self.scene())
        client = FakeQc(0.95)
        llm_runner.run_qc(self.p, jid, client, self.data)
        self.assertIn("1. KELLY (nhân vật)", client.prompts[0])
        labels = [label for label, _ in client.images[0]]
        self.assertEqual(labels[0], "Ảnh cần chấm điểm:")
        self.assertTrue(any("Ảnh tham chiếu 1 — KELLY" in x for x in labels))

    def test_a_weapon_or_prop_the_scene_names_is_a_reference_but_not_a_prop_named_like_a_character(self):
        for name, kind, seed in (("Katana", "weapon", 2), ("kelly", "prop", 3), ("Balo", "prop", 4)):
            aid = assets.create(self.p.conn, "FF", kind, name, "", "", None, "x")
            assets.add_image(self.p.conn, aid, f"{name}.png", png(seed))
            assets.attach(self.p.conn, self.pid, aid)
        refs = assets.scene_references(self.p.conn, self.pid, {"characters": ["Kelly"], "text": "Kelly rút katana ra khỏi vỏ", "image_prompt": ""})
        self.assertEqual([(r["label"], r["role"]) for r in refs], [("Katana", "object")])       # Balo is not in the scene; "kelly" the prop is the cast member
        self.assertIn("Image 1 is the object Katana", assets.reference_note(refs))


class BackgroundCheckTests(Base):
    def wait(self):
        for _ in range(200):
            if not autoqc.active(self.pid):
                return
            time.sleep(0.05)
        self.fail("the background check did not finish")

    def test_the_background_check_scores_every_generated_picture_and_fixes_the_faulty_ones(self):
        good, bad = self.generated_job(self.scene(1)), self.generated_job(self.scene(2))
        answers = iter([0.95, 0.3])

        class Alternating(FakeQc):
            def complete(inner, prompt, images=()):
                inner.score = next(answers)
                return FakeQc.complete(inner, prompt, images)
        self.assertTrue(autoqc.start(self.db, self.data, self.pid, lambda: Alternating()))
        self.wait()
        by_id = {s[0]: s for s in self.states()}
        self.assertEqual(by_id[good][1], "pending_review")
        self.assertEqual(by_id[bad][1], "rejected")
        self.assertTrue(any(s[1] == "queued" and s[2] == 1 for s in by_id.values()))            # the automatic fix is waiting to be sent
        self.assertEqual(autoqc.waiting(self.p.conn, self.pid), 0)

    def test_a_check_that_cannot_run_is_reported_once_and_not_looped(self):
        jid = self.generated_job(self.scene())

        class Broken:
            def complete(self, prompt, images=()):
                raise llm_runner.LlmError("Claude Code chưa đăng nhập", code="auth")
        self.assertTrue(autoqc.start(self.db, self.data, self.pid, lambda: Broken()))
        self.wait()
        self.assertIn("chưa đăng nhập", autoqc.last_error(self.pid))
        self.assertEqual(self.p.state(jid).value, "succeeded")                                    # still waiting: nothing was thrown away
        self.assertFalse(autoqc.start(self.db, self.data, self.pid, lambda: FakeQc()))            # not retried in a loop
        autoqc.clear_error(self.pid)
        self.assertTrue(autoqc.start(self.db, self.data, self.pid, lambda: FakeQc(0.95)))
        self.wait()
        self.assertEqual(self.p.state(jid).value, "pending_review")

    def test_nothing_starts_without_a_claude_or_without_pictures(self):
        self.assertFalse(autoqc.start(self.db, self.data, self.pid, lambda: FakeQc()))            # no pictures yet
        self.generated_job(self.scene())
        self.assertFalse(autoqc.start(self.db, self.data, self.pid, lambda: None))                # no Claude configured


class RaceTests(Base):
    def test_a_picture_already_judged_by_another_check_is_skipped_not_a_crash(self):
        jid = self.generated_job(self.scene())
        self.assertEqual(llm_runner.run_qc(self.p, jid, FakeQc(0.95), self.data)["decision"], "pending_review")
        # a second, concurrent check (the old race: a manual click and the background thread landing on the same picture)
        self.assertEqual(self.p.apply_qc(jid, {"character": 0.9}), "already_processed")
        self.assertEqual(self.p.state(jid).value, "pending_review")            # untouched by the second check

    def test_auto_mode_projects_are_not_polled_for_automatic_qc(self):
        """"auto" mode already runs its own QC via autopilot; the dashboard page must not start a second, racing check."""
        from unittest import mock
        from streamlit.testing.v1 import AppTest
        from core.adapters import factory
        from tests.test_step1_flow import APP
        self.p.set_mode(self.pid, "auto")
        self.generated_job(self.scene())
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": self.data})
        try:
            with mock.patch.object(factory, "image_provider", return_value=self.provider), \
                    mock.patch("core.llm_runner.client_from_env", return_value=FakeQc(0.95)):
                at = AppTest.from_file(APP, default_timeout=60)
                at.query_params["step"] = "2"
                at.run()
            self.assertFalse(at.exception)
        finally:
            os.environ.pop("PIPELINE_DB", None)
            os.environ.pop("PIPELINE_DATA", None)
        self.assertFalse(autoqc.active(self.pid))


if __name__ == "__main__":
    unittest.main()
