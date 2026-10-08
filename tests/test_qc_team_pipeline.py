"""Tổ QC trong pipeline (cờ qc_team, 01/10): thay lớp 1 của QC theo cảnh, mọi khung chờ người kèm ghi chú, lỗi trái/phải không tự chặn."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import qc_scene, qc_team
from core.db import connect
from core.pipeline import Pipeline
from tests._flags import flags_on
from tests.test_qc_team import FakeClient


class TeamInPipelineTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.dir = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t", operating_mode="human_qc", threshold=0.5)
        self.frames = []
        for idx in (1, 2):
            sid = self.p.create_scene(self.pid, idx)
            data = {"shot_no": idx, "characters": ["MAXIM"], "story_scene": 1, "size": "MS",
                    "blocking": "over MAXIM's shoulder" if idx == 2 else "MAXIM frame-left facing camera"}
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
            self.p.conn.commit()
            jid = self.p.create_job(sid, "image_gen")
            self.p.start(jid), self.p.succeed(jid)
            folder = os.path.join(self.dir, str(self.pid), "images")
            os.makedirs(folder, exist_ok=True)
            Image.new("RGB", (360, 640), (120, 160, 220)).save(os.path.join(folder, f"job_{jid}.png"))
        self.env = mock.patch.dict(os.environ, {})
        self.env.start()
        flags_on(self, "qc_team", "scene_qc")      # B1 học việc 08/10: FEATURE_X=1 = học việc; really ON only from 🧪

    def tearDown(self):
        self.env.stop()

    def test_layer_one_is_the_team_and_every_frame_waits_for_the_person_with_a_note(self):
        self.assertTrue(qc_scene.claude_on())
        client = FakeClient(false_types={"count"})
        r = qc_scene.run_ready_scenes(self.p, self.pid, client, self.dir)
        self.assertEqual(r["failed"], [])
        self.assertEqual(len(client.calls), 2)                              # one structured call per frame
        for (jid,) in self.p.conn.execute("SELECT id FROM jobs WHERE project_id=?", (self.pid,)):
            self.assertEqual(self.p.job(jid)["state"], "pending_review")    # never approved / redrawn on its own
            note = self.p.conn.execute("SELECT note FROM job_events WHERE job_id=? ORDER BY id DESC LIMIT 1", (jid,)).fetchone()[0]
            self.assertIn("Tổ QC (thử", note)
        with open(os.path.join(self.dir, str(self.pid), "qc_scene", "team.json"), encoding="utf-8") as f:
            self.assertEqual(len(json.load(f)), 2)
        again = qc_scene.run_ready_scenes(self.p, self.pid, client, self.dir)
        self.assertEqual((again["reviewed"], len(client.calls)), ([], 2))  # the same pictures are not paid for twice

    def test_without_a_structured_claude_it_stops_and_says_so(self):
        class Plain:
            pass
        r = qc_scene.run_ready_scenes(self.p, self.pid, Plain(), self.dir)
        self.assertIn("LLM_PROVIDER=anthropic", r["failed"][0][1])

    def test_the_cost_estimate_counts_the_team(self):
        from core import cost
        self.assertEqual(cost._picture_qc_calls(self.p.conn, self.pid, 4), 0)   # counted apart, per frame
        self.assertGreater(qc_team.FRAME_USD, 0)


class TeamTraineeTests(TeamInPipelineTests):
    """B5 học việc 08/10: qc_team 🎓 — the same looks, block/pass only in trainee_log; no hold note, no team.json, its own ledger tag."""

    def setUp(self):
        super().setUp()
        from tests._flags import flags_off, flags_trainee
        flags_trainee(self, "qc_team")
        flags_off(self, "scene_qc_claude", "qc_agent")

    def test_layer_one_is_the_team_and_every_frame_waits_for_the_person_with_a_note(self):
        from core import llm_runner
        self.assertFalse(qc_scene.claude_on())                              # học việc never counts as the layer-1 Claude
        tags = []

        class Tagged(FakeClient):
            def ask_json(s, *a, **kw):
                tags.append(llm_runner.current_tag()[0])
                return FakeClient.ask_json(s, *a, **kw)
        client = Tagged(false_types={"count"})
        r = qc_scene.run_ready_scenes(self.p, self.pid, client, self.dir)
        self.assertEqual(r["failed"], [])
        self.assertEqual(len(client.calls), 2)                              # it still looks at every frame
        self.assertEqual(set(tags), {"trainee_qc_team"})
        for (jid,) in self.p.conn.execute("SELECT id FROM jobs WHERE project_id=?", (self.pid,)):
            self.assertEqual(self.p.job(jid)["state"], "pending_review")    # the "QC Claude tắt" branch: waits for the person
            notes = " ".join(n or "" for (n,) in self.p.conn.execute("SELECT note FROM job_events WHERE job_id=?", (jid,)))
            self.assertNotIn("Tổ QC", notes)                                # blind: no verdict before the person decides
        self.assertFalse(os.path.exists(os.path.join(self.dir, str(self.pid), "qc_scene", "team.json")))
        rows = self.p.conn.execute("SELECT feature, decision, subject, job_id, cost_usd FROM trainee_log").fetchall()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(x["feature"] == "qc_team" and x["decision"] in ("block", "pass") for x in rows))
        with open(os.path.join(self.dir, str(self.pid), "qc_scene", "reviews.json"), encoding="utf-8") as f:
            marks = json.load(f)["1"]
        self.assertTrue(any(m.get("trainee") for m in marks))
        self.assertFalse(any("team" in m for m in marks))
        again = qc_scene.run_ready_scenes(self.p, self.pid, client, self.dir)
        self.assertEqual(len(client.calls), 2)                              # the same pictures are not paid for twice
        self.assertEqual(again["failed"], [])

    def test_without_a_structured_claude_it_stops_and_says_so(self):
        class Plain:
            pass
        r = qc_scene.run_ready_scenes(self.p, self.pid, Plain(), self.dir)
        self.assertEqual(r["failed"], [])                                   # học việc never stops the project
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM trainee_log").fetchone()[0], 0)

    def test_the_cost_estimate_counts_the_team(self):
        from core import cost, project_budget
        self.assertEqual(cost._picture_qc_calls(self.p.conn, self.pid, 4), 0)   # the old per-picture QC does not come back
        self.assertEqual(project_budget.claude_stage("trainee_qc_team"), "claude_qc")
        est = {"total": 1, "max": 2, "images": 0.1, "videos": 0, "llm": 0.5, "trainee": 0.12, "unknown": [], "llm_left": None,
               "counts": {"images": 4, "clips": 0, "seconds": 0}}
        self.assertIn("(học việc)", cost.format_run_estimate(est))


if __name__ == "__main__":
    unittest.main()
