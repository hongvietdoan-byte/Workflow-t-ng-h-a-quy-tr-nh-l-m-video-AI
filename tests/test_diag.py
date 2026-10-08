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


class StageNameTests(unittest.TestCase):
    """S14.4 C1b (04/10): a stage written under another name ('videos', 'images', 'delivery'...) disappeared from the table."""

    def test_aliases_are_folded_to_one_name(self):
        for raw, want in (("videos", "video"), ("images", "image"), ("image_gen", "image"), ("video_gen", "video"),
                          ("delivery", "render"), ("translate", "motion"), (" Video ", "video"), ("voice", "voice"), ("weird", "weird")):
            self.assertEqual(diag.normalize_stage(raw), want, raw)
        self.assertEqual(diag.normalize_stage("lipsync"), "lipsync")          # no 'lipsync -> video' (nobody writes it)
        self.assertIn("voice", diag.STAGE_LABEL)

    def test_record_stores_the_folded_name_and_the_table_counts_old_rows_too(self):
        conn = connect()
        diag.record(conn, "videos", "warn", "a")
        conn.execute("INSERT INTO diag_events (at, last_at, stage, severity, message, count) VALUES (?,?,?,?,?,1)",
                     (diag._now(), diag._now(), "images", "error", "old row"))            # written before the fix
        diag.record(conn, "voice", "warn", "tts")
        diag.record(conn, "made_up", "warn", "x")
        conn.commit()
        self.assertEqual([r["stage"] for r in conn.execute("SELECT stage FROM diag_events WHERE message='a'")], ["video"])
        rows = {s["stage"]: s for s in diag.stage_table(conn)}
        self.assertEqual((rows["video"]["warn"], rows["image"]["error"], rows["voice"]["warn"]), (1, 1, 1))
        self.assertEqual(rows["other"]["warn"], 1)                                   # an unknown stage is not lost

    def test_every_constant_stage_in_the_code_is_a_known_one(self):
        """Scan: diag.record(conn, "<stage>"…), autopilot._d(p, pid, "<stage>"…), llm_runner._diagnosed("<stage>")."""
        import ast
        root = os.path.join(os.path.dirname(__file__), "..")
        known, bad = {s for s, _ in diag.STAGES}, []
        for top in ("core", "dashboard"):
            for dp, _, fs in os.walk(os.path.join(root, top)):
                for f in fs:
                    if not f.endswith(".py"):
                        continue
                    path = os.path.join(dp, f)
                    for n in ast.walk(ast.parse(open(path, encoding="utf-8").read())):
                        if not isinstance(n, ast.Call):
                            continue
                        fn = n.func
                        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                        base = getattr(getattr(fn, "value", None), "id", "")
                        pos = {("diag", "record"): 1, ("", "_d"): 2, ("", "_diagnosed"): 0, ("", "_run"): 2,
                               ("claude_tasks", "_run"): 2, ("", "_retry_note"): 1, ("", "_note"): 1}.get((base, name))
                        if pos is None or len(n.args) <= pos:
                            continue
                        a = n.args[pos]
                        # _run's stage is also the cost tag (llm_runner.tagged): an alias ('translate') is fine there
                        ok = known | set(diag.STAGE_ALIASES) if name == "_run" else known
                        if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value not in ok:
                            bad.append(f"{os.path.relpath(path, root)}:{n.lineno} {a.value!r}")
        self.assertEqual(bad, [])

    def test_devsys_areas_use_known_stages(self):
        import json
        cfg = json.load(open(os.path.join(os.path.dirname(__file__), "..", "devsys", "areas.json"), encoding="utf-8"))
        known = {s for s, _ in diag.STAGES}
        used = [s for a in cfg["areas"] for s in a.get("diag_stages", [])]
        self.assertEqual([s for s in used if s not in known], [])
        self.assertIn("voice", used)


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
        found = [e for e in events(p, "image") if e["code"] != "missing_reference"]   # 2026-09-26: the shot's missing references
        self.assertEqual(len(found), 1)                                                 # are noted too (info, luật 1)
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
        found = [e for e in events(self.p, "director") if e["severity"] != "info" and e["code"] != "prompt_formula"]   # F1: formula check notes are their own    # info: which pictures the Director saw
        self.assertEqual([e["code"] for e in found], ["bad_json_retry"])

    def test_llm_failure_is_recorded_and_still_raised(self):
        self.build()

        class Broken:
            def complete(self, prompt, images=()):
                raise llm_runner.LlmError("Anthropic rejected the API key (HTTP 401)", code="auth")

        with self.assertRaises(llm_runner.LlmError):
            llm_runner.run_director(self.p, self.pid, Broken())
        found = [e for e in events(self.p, "director") if e["severity"] != "info" and e["code"] != "prompt_formula"]   # F1: formula check notes are their own
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
        self.assertIn("voice", rows)                       # S14.4 C1b: the TTS stage has its own row
        self.assertNotIn(diag.OTHER, rows)                 # 'Khác' only appears when an unknown stage was written


if __name__ == "__main__":
    unittest.main()
