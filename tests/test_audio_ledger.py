import os
import sqlite3
import tempfile
import unittest

from core import cost, music
from core.db import connect
from core.pipeline import Pipeline

OLD_SCHEMA = """
CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL, operating_mode TEXT NOT NULL DEFAULT 'human_qc',
  qc_auto_pass_threshold REAL NOT NULL DEFAULT 0.85, max_retry_count INTEGER NOT NULL DEFAULT 3, created_at TEXT NOT NULL);
CREATE TABLE scenes (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, idx INTEGER NOT NULL, title TEXT,
  state TEXT NOT NULL DEFAULT 'ready', data TEXT, UNIQUE (project_id, idx));
CREATE TABLE jobs (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, scene_id INTEGER NOT NULL, type TEXT NOT NULL,
  state TEXT NOT NULL, parent_job_id INTEGER, retry_count INTEGER NOT NULL DEFAULT 0, retry_reason TEXT,
  escalated INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE usage_events (id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id),
  kind TEXT NOT NULL CHECK (kind IN ('image','video')), provider TEXT NOT NULL, model TEXT NOT NULL,
  tier TEXT NOT NULL, quantity REAL NOT NULL, unit TEXT NOT NULL, at TEXT NOT NULL);
INSERT INTO projects (id, name, created_at) VALUES (7, 'old', 'x');
INSERT INTO scenes (id, project_id, idx) VALUES (1, 7, 1);
INSERT INTO jobs (id, project_id, scene_id, type, state, created_at, updated_at) VALUES (5, 7, 1, 'video_gen', 'succeeded', 'x', 'x');
INSERT INTO usage_events (job_id, kind, provider, model, tier, quantity, unit, at) VALUES (5, 'video', 'clipai', 'm', '720p', 5, 'second', 'x');
"""


class AudioLedgerTests(unittest.TestCase):
    def test_old_database_is_migrated_and_keeps_rows(self):
        tmp = os.path.join(tempfile.mkdtemp(), "old.sqlite")
        raw = sqlite3.connect(tmp)
        raw.executescript(OLD_SCHEMA)
        raw.commit()
        raw.close()
        conn = connect(tmp)
        row = conn.execute("SELECT job_id, project_id, kind, quantity FROM usage_events").fetchone()
        self.assertEqual((row["job_id"], row["project_id"], row["kind"], row["quantity"]), (5, 7, "video", 5))
        cost.record_usage(conn, None, "audio", "clipai-audio", "music_v2", "default", 1, "item", project_id=7)
        self.assertEqual(conn.execute("SELECT COUNT(*) c FROM usage_events").fetchone()["c"], 2)
        connect(tmp)  # second open must not migrate again or fail

    def test_music_submissions_are_recorded_and_priced(self):
        p = Pipeline(connect())
        pid = p.create_project("t")
        drafts, _ = music.project_dirs(tempfile.mkdtemp(), pid)

        class Real(music.MockAudioProvider):
            name = "clipai-audio"

        music.submit_drafts(Real(), drafts, "calm", 5000, True, 3, ledger=(p.conn, pid))
        summary = cost.spend_summary(p.conn, pid, cost.load_pricing())
        self.assertEqual(summary["audios"], 3)
        self.assertIn("music_v2", summary["unknown_prices"])
        priced = cost.load_pricing()
        priced["per_audio"]["music_v2"] = 2.5
        self.assertEqual(cost.spend_summary(p.conn, pid, priced)["credits"], 7.5)

    def test_mock_audio_is_not_billed_and_no_ledger_is_fine(self):
        p = Pipeline(connect())
        pid = p.create_project("t")
        drafts, _ = music.project_dirs(tempfile.mkdtemp(), pid)
        music.submit_drafts(music.MockAudioProvider(), drafts, "calm", 5000, True, 2)  # no ledger
        self.assertEqual(cost.spend_summary(p.conn, pid, cost.load_pricing())["audios"], 0)
        music.submit_drafts(music.MockAudioProvider(), drafts, "calm", 5000, True, 1, ledger=(p.conn, pid))
        priced = cost.load_pricing()
        priced["per_audio"]["music_v2"] = 9
        summary = cost.spend_summary(p.conn, pid, priced)
        self.assertEqual((summary["audios"], summary["credits"]), (0, 0.0))  # mock is never recorded


if __name__ == "__main__":
    unittest.main()
