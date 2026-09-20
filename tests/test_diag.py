import os
import tempfile
import unittest

from core import autopilot, diag, llm_runner
from core.db import connect
from core.llm_runner import LlmReply
from core.pipeline import Pipeline
from core.providers import MockImageProvider, MockVideoProvider, ProviderError
from core.runner import ImageRunner
from tests.test_autopilot import Setup


def events(p, stage=None):
    sql = "SELECT * FROM diag_events" + (" WHERE stage=?" if stage else "")
    return p.conn.execute(sql, (stage,) if stage else ()).fetchall()


class RecordTests(unittest.TestCase):
    def test_repeats_are_merged_and_secrets_are_masked(self):
        conn = connect()
        for _ in range(5):
            diag.record(conn, "video", "warn", "HTTP 429", "rate_limited", 1)
        rows = conn.execute("SELECT count FROM diag_events").fetchall()
        self.assertEqual([r["count"] for r in rows], [5])                                # one row, counter 5
        diag.record(conn, "video", "warn", "HTTP 429", "rate_limited", 2)                 # other project = other row
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM diag_events").fetchone()[0], 2)
        diag.record(conn, "system", "error", "Authorization: Bearer abcdef1234567890abcdef and sk-ant-abcdefghijk1234", None)
        text = " ".join(r["message"] for r in conn.execute("SELECT message FROM diag_events"))
        self.assertNotIn("abcdef1234567890", text)
        self.assertNotIn("sk-ant-abcdefghijk", text)

    def test_recording_never_raises(self):
        conn = connect()
        conn.execute("DROP TABLE diag_events")
        diag.record(conn, "video", "error", "x")          # watching must not break the work


class HookTests(Setup):
    def test_transient_and_permanent_provider_problems_are_seen(self):
        self.build()
        p = self.p

        class Flaky(MockImageProvider):
            def submit(self, prompt):
                raise ProviderError("rate limited (HTTP 429)", code="rate_limited", transient=True)

        scene = p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,)).fetchone()["id"]
        p.create_job(scene, "image_gen")
        runner = ImageRunner(p, Flaky(), self.data)
        runner.submit_pending(self.pid)
        found = events(p, "image")
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["severity"], found[0]["code"]), ("warn", "rate_limited"))
        self.assertEqual(p.conn.execute("SELECT state FROM jobs WHERE scene_id=?", (scene,)).fetchone()["state"], "queued")

    def test_a_model_answer_that_needed_a_second_try_is_recorded(self):
        self.build()

        class TwiceBad:
            def __init__(self):
                self.inner, self.calls = llm_runner.MockLlm(), 0

            def complete(self, prompt, images=()):
                self.calls += 1
                return LlmReply("không phải JSON", 1, 1) if self.calls == 1 else self.inner.complete(prompt, images)

        llm_runner.run_director(self.p, self.pid, TwiceBad())
        found = events(self.p, "director")
        self.assertEqual([e["code"] for e in found], ["bad_json_retry"])

    def test_llm_failure_is_recorded_and_still_raised(self):
        self.build()

        class Broken:
            def complete(self, prompt, images=()):
                raise llm_runner.LlmError("Anthropic rejected the API key (HTTP 401)", code="auth")

        with self.assertRaises(llm_runner.LlmError):
            llm_runner.run_director(self.p, self.pid, Broken())
        found = events(self.p, "director")
        self.assertEqual((found[0]["severity"], found[0]["code"]), ("error", "auth"))

    def test_music_failure_that_silently_drops_the_soundtrack_is_flagged(self):
        ctx = self.build(audio=True)

        class NoMusic:
            def generate_music(self, *a, **k):
                raise ProviderError("no credit", code="http_error")

        ctx.audio = None
        autopilot._d(self.p, self.pid, "music", "warn", "nhạc nền không tạo được, video cuối sẽ KHÔNG có nhạc", "degraded")
        self.assertTrue(any(f["code"] == "degraded" for f in events(self.p, "music")))


class ScanTests(Setup):
    def test_silent_problems_are_found(self):
        self.build()
        p = self.p
        scene = p.conn.execute("SELECT id FROM scenes WHERE project_id=? LIMIT 1", (self.pid,)).fetchone()["id"]
        old = "2020-01-01T00:00:00+00:00"
        j1 = p.create_job(scene, "video_gen")
        p.conn.execute("UPDATE jobs SET state='running', updated_at=? WHERE id=?", (old, j1))            # stuck for years
        j2 = p.create_job(scene, "image_gen")
        p.conn.execute("UPDATE jobs SET state='succeeded', result_path=? WHERE id=?", ("/nope/missing.png", j2))  # no file
        p.conn.execute("UPDATE projects SET autopilot_state='running', autopilot_beat=1 WHERE id=?", (self.pid,))  # nobody ticking
        p.conn.commit()
        titles = " | ".join(f["title"] for f in diag.scan(p.conn, self.data))
        self.assertIn(f"Job #{j1} chạy", titles)
        self.assertIn(f"Job #{j2} báo xong nhưng không có file", titles)
        self.assertIn("không có tiến trình nào tick", titles)

    def test_a_healthy_finished_run_has_no_findings_and_the_report_hides_secrets(self):
        ctx = self.build()
        autopilot.start(self.p, self.pid)
        autopilot.run_until_done(self.p, self.pid, ctx)
        self.assertEqual([f for f in diag.scan(self.p.conn, self.data) if f["severity"] == "error"], [])
        os.environ["CLIPAI_TOKEN"] = "SECRETTOKENVALUE1234567890"
        try:
            diag.record(self.p.conn, "video", "error", "failed with token=SECRETTOKENVALUE1234567890", "x", self.pid)
            text = diag.report(self.p.conn, self.data)
        finally:
            os.environ.pop("CLIPAI_TOKEN", None)
        self.assertNotIn("SECRETTOKENVALUE", text)
        self.assertIn("## Từng khâu", text)
        self.assertIn("Gen video", text)
        rows = {s["stage"]: s for s in diag.stage_table(self.p.conn)}
        self.assertGreater(rows["video"]["ok"], 0)
        self.assertEqual(diag.health(rows["image"]), "🟢")


if __name__ == "__main__":
    unittest.main()
