"""S14.1 A1b + S14.3 B1b — post lip sync (sync.so) through the money gate (core.spend_gate) and a time limit on 'running'.

Before: lipsync.post_tick checked the trial cap only (no locked project budget), wrote the ledger row without project_id, marked the
shot 'running' only after the ledger row (a ledger error lost a paid task → sent again next tick), and a sync.so task 'COMPLETED' with
no outputUrl was polled forever. Fake providers only — 0 USD, no real API."""
import os
import time
import unittest
from unittest import mock

from core import lipsync, project_budget
from core.pipeline import PipelinePaused
from core.providers import TaskStatus
from tests.test_trial_fixes import Base, codes

ON = {"FEATURE_PROJECT_BUDGET": "1"}


def lock(p, pid, videos=5.0):
    project_budget.approve(p, pid, "a@x", {"stages": {k: {"cap": videos if k == "videos" else 5.0} for k in project_budget.STAGES},
                                           "total": 100.0})


class Sync:
    """A lip-sync provider NOT named mock*: the caps apply to it as to sync.so."""
    name = "syncso"

    def __init__(self, model="lipsync-2-pro", status=None):
        self.model, self._status, self.sent = model, status, []

    def submit(self, video, audio):
        self.sent.append(video)
        return f"T{len(self.sent)}"

    def status(self, task):
        return self._status or TaskStatus("running")

    def download(self, task, dest):
        with open(dest, "wb") as f:
            f.write(b"SYNCED")
        return dest


class LipSyncGateTests(Base):
    def setUp(self):
        super().setUp()
        self.set_data({"image_prompt": "x", "characters": ["KELLY"], "size": "MS", "shot_no": 1,
                       "dialogue": [{"speaker": "KELLY", "text": "Em hiểu rồi."}]})
        self.jid, self.clip = self.finished_clip()
        self.seg = os.path.join(self.dir, "seg.wav")
        open(self.seg, "wb").close()
        self.patches = [mock.patch("core.lipsync.shot_audio", return_value={"path": self.seg, "offsets": [0.3], "lines": [1], "seconds": 4}),
                        mock.patch("core.final_cut.clip_seconds", return_value=4.0)]
        for x in self.patches:
            x.start()

    def tearDown(self):
        for x in self.patches:
            x.stop()
        super().tearDown()

    def rows(self):
        return self.p.conn.execute("SELECT * FROM usage_events").fetchall()

    def rec(self):
        return lipsync.index(self.dir, self.pid).get(str(self.sid)) or {}

    @mock.patch.dict(os.environ, ON)
    def test_a_model_without_a_price_is_refused_before_sending_when_the_project_is_locked(self):
        lock(self.p, self.pid)
        provider = Sync(model="lipsync-2")                       # null in data/pricing.json
        c = lipsync.post_tick(self.p, self.pid, self.dir, provider, "ffmpeg")
        self.assertEqual(provider.sent, [])                       # nothing sent …
        self.assertEqual(self.rows(), [])                         # … and no unpriced 'videos' row blocking every clip of the project
        self.assertEqual(c["sent"], 0)
        self.assertTrue(any("CHƯA CÓ GIÁ" in m for m in codes(self.p, "budget")))

    @mock.patch.dict(os.environ, ON)
    def test_the_locked_video_budget_is_checked(self):
        lock(self.p, self.pid, videos=0.2)                        # 4 s × 0.084 = 0.336 > 0.2
        provider = Sync()
        lipsync.post_tick(self.p, self.pid, self.dir, provider, "ffmpeg")
        self.assertEqual(provider.sent, [])
        self.assertTrue(any("chạm trần" in m for m in codes(self.p, "budget")))

    def test_the_ledger_row_carries_the_project_and_the_lipsync_label(self):
        provider = Sync()
        c = lipsync.post_tick(self.p, self.pid, self.dir, provider, "ffmpeg")
        self.assertEqual(c["sent"], 1)
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["project_id"], rows[0]["stage"], rows[0]["kind"]), (self.pid, "lipsync", "video"))
        self.assertEqual(rows[0]["job_id"], self.jid)

    def test_the_shot_is_marked_running_right_after_the_send(self):
        """A ledger error after the send must not lose the paid task (else the next tick pays again)."""
        provider = Sync()
        with mock.patch("core.cost.record_usage", side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                lipsync.post_tick(self.p, self.pid, self.dir, provider, "ffmpeg")
        self.assertEqual((self.rec().get("state"), self.rec().get("task")), ("running", "T1"))
        lipsync.post_tick(self.p, self.pid, self.dir, provider, "ffmpeg")
        self.assertEqual(len(provider.sent), 1)                   # not sent a second time

    def test_a_paused_project_raises_pipeline_paused_and_sends_nothing(self):
        self.p.conn.execute("UPDATE projects SET paused=1 WHERE id=?", (self.pid,))
        self.p.conn.commit()
        provider = Sync()
        with self.assertRaises(PipelinePaused):
            lipsync.post_tick(self.p, self.pid, self.dir, provider, "ffmpeg")
        self.assertEqual(provider.sent, [])

    def test_a_task_running_past_the_time_limit_fails_with_a_note(self):
        provider = Sync()
        lipsync.post_tick(self.p, self.pid, self.dir, provider, "ffmpeg")
        self.assertIn("sent_at", self.rec())
        c = lipsync.post_tick(self.p, self.pid, self.dir, provider, "ffmpeg")
        self.assertEqual(c["running"], 1)                         # inside the limit: still waiting
        lipsync.mark(self.dir, self.pid, self.sid, sent_at=time.time() - lipsync.RUNNING_LIMIT_S - 5)
        c = lipsync.post_tick(self.p, self.pid, self.dir, provider, "ffmpeg")
        self.assertEqual((c["failed"], c["running"]), (1, 0))
        self.assertEqual(self.rec()["state"], "failed")
        notes = codes(self.p, "lipsync_timeout")
        self.assertEqual(len(notes), 1)
        self.assertIn("quá hạn chờ", notes[0])
        with open(self.clip, "rb") as f:
            self.assertEqual(f.read(), b"ORIGINAL-CLIP")          # the clip keeps its own mouth
        lipsync.post_tick(self.p, self.pid, self.dir, provider, "ffmpeg")
        self.assertEqual(len(provider.sent), 1)                   # said once; not sent again for the same clip

    def test_an_old_running_record_without_a_send_time_starts_its_clock(self):
        lipsync.mark(self.dir, self.pid, self.sid, state="running", task="OLD", job_id=self.jid)
        c = lipsync.post_tick(self.p, self.pid, self.dir, Sync(), "ffmpeg")
        self.assertEqual(c["running"], 1)
        self.assertIn("sent_at", self.rec())


if __name__ == "__main__":
    unittest.main()
