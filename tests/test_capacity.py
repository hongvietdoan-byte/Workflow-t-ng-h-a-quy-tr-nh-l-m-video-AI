"""Kế hoạch V4 6.3: system limits measured from a (fake) job history — the numbers match a hand calculation, and too few samples
give "chưa đủ dữ liệu" instead of a guess."""
import unittest

from core import capacity
from core.db import connect
from core.pipeline import Pipeline


def _job(p, sid, model, t0, t_run, t_end, outcome="succeeded", clip_s=5.0, leader=None, retry=None):
    cur = p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, model, created_at, updated_at, retry_reason, group_leader)"
                         " VALUES (1, ?, 'video_gen', ?, ?, ?, ?, ?, ?)",
                         (sid, outcome, model, f"2026-09-25T10:{t0:02d}:00+00:00", f"2026-09-25T10:{t_end:02d}:00+00:00", retry, leader))
    jid = cur.lastrowid
    for frm, to, t in ((None, "queued", t0), ("queued", "running", t_run), ("running", outcome, t_end)):
        p.conn.execute("INSERT INTO job_events (job_id, from_state, to_state, actor, at) VALUES (?,?,?,?,?)",
                       (jid, frm, to, "system", f"2026-09-25T10:{t:02d}:00+00:00"))
    p.conn.execute("INSERT OR REPLACE INTO motion_prompts (scene_id, motion_prompt, duration_sec) VALUES (?,?,?)", (sid, "x", clip_s))
    return jid


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("cap")
        self.sids = [self.p.create_scene(self.pid, i, f"s{i}") for i in range(1, 8)]

    def test_numbers_match_a_hand_calculation(self):
        # three real runs of 2, 4 and 6 minutes (the 2nd and 3rd overlap), one failure, one multi-shot follower that "ran" 0 min
        _job(self.p, self.sids[0], "kling", 0, 1, 3)
        a = _job(self.p, self.sids[1], "kling", 0, 5, 9)
        _job(self.p, self.sids[2], "kling", 0, 6, 12)
        _job(self.p, self.sids[3], "kling", 0, 20, 21, outcome="failed", retry="retry sau lỗi rate-limit 1130")
        _job(self.p, self.sids[4], "kling", 0, 9, 9, leader=a)
        self.p.conn.commit()
        m = capacity.measured(self.p.conn)["video_gen"]
        k = m["models"]["kling"]
        self.assertEqual(k["n"], 5)
        self.assertEqual(k["run_s"], {"median": 240.0, "p90": 336.0, "n": 3})       # 120, 240, 360 s → P90 = 240 + 0.8 × 120
        self.assertEqual(k["not_a_run"], 1)
        self.assertEqual(k["fail_rate"], 0.2)
        self.assertEqual(k["rate_limited"], 1)
        self.assertEqual(k["run_per_clip_s"]["median"], 48.0)                     # 240 s / 5 s of clip
        self.assertEqual(m["peak"], 2)                                            # 10:06–10:09 two run at once
        self.assertEqual(capacity.confidence(k["n"]), "thấp")
        e = capacity.estimate(self.p.conn, 20)
        self.assertEqual((e["clips"], e["concurrency"]), (10, 2))                 # 20 s ÷ 2 s shots; ClipAI cap 2
        self.assertEqual(e["minutes"], round(5 * 240 / 60, 1))                    # 5 waves × 240 s = 20 min

    def test_too_few_samples_say_so(self):
        _job(self.p, self.sids[0], "kling", 0, 1, 3)
        self.p.conn.commit()
        e = capacity.estimate(self.p.conn, 60)
        self.assertIsNone(e["minutes"])
        self.assertIn("chưa đủ dữ liệu", e["note"])


if __name__ == "__main__":
    unittest.main()
