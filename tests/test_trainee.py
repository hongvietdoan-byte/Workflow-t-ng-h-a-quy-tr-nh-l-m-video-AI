"""B2 học việc (08/10, docs/KE_HOACH_HOC_VIEC_2026-10-08.md mục 2–3): bảng trainee_log + core/trainee.py (ghi, chấm, độ khớp, ngưỡng)."""
import os
import tempfile
import unittest
from unittest import mock

from core import trainee
from core.db import connect
from core.pipeline import Pipeline

T0 = "2026-10-08T10:00:00+00:00"
T_BEFORE = "2026-10-08T09:00:00+00:00"
T_AFTER = "2026-10-08T11:00:00+00:00"


class TraineeTests(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "m.sqlite")
        env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": tempfile.mkdtemp()})
        env.start()
        self.addCleanup(env.stop)
        self.conn = connect(self.db)
        self.p = Pipeline(self.conn)

    def _project(self, name="Dự án học việc"):
        pid = self.p.create_project(name)
        sid = self.p.create_scene(pid, 1, "c1")
        return pid, sid

    def _frames(self, pid, sid, decisions, truths, at=T0, decided=T_AFTER, feature="qc_team"):
        """One image job per frame: the role's decision recorded at `at`, the person's review_log decision at `decided`."""
        for d, t in zip(decisions, truths):
            jid = self.p.create_job(sid, "image_gen")
            trainee.record(self.conn, feature, pid, f"job:{jid}", d, job_id=jid, scene_id=sid, at=at)
            self.conn.execute("INSERT INTO review_log (job_id, reviewer_type, decision, note, decided_at) VALUES (?,?,?,?,?)",
                              (jid, "user", t, None, decided))
        self.conn.commit()

    def test_schema(self):
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(trainee_log)")}
        for c in ("at", "feature", "project_id", "scene_id", "job_id", "story_scene", "subject", "decision", "would_do", "detail",
                  "cost_usd", "truth", "truth_source", "match", "scored_at"):
            self.assertIn(c, cols)
        idx = {r[1] for r in self.conn.execute("PRAGMA index_list(trainee_log)")}
        self.assertIn("idx_trainee_log", idx)
        self.assertEqual(set(trainee.RULES), {"qc_team", "scene_qc", "scene_establishing", "camera_setups", "continuous_takes",
                                              "end_frames", "storyboard_auto_trust"})

    def test_record_rejects_unknown(self):
        pid, _ = self._project()
        with self.assertRaises(ValueError):
            trainee.record(self.conn, "j_cut", pid, "job:1", "block")
        with self.assertRaises(ValueError):
            trainee.record(self.conn, "qc_team", pid, "job:1", "group")
        rid = trainee.record(self.conn, "qc_team", pid, "job:1", "block", would_do={"hold": True}, detail={"why": "mắt"}, cost_usd=0.03)
        row = self.conn.execute("SELECT * FROM trainee_log WHERE id=?", (rid,)).fetchone()
        self.assertEqual((row["decision"], row["cost_usd"]), ("block", 0.03))
        self.assertIn("hold", row["would_do"])
        self.assertIsNone(row["truth"])

    def test_score_uses_the_person_decision_after_the_role(self):
        pid, sid = self._project()
        self._frames(pid, sid, ["block", "pass"], ["reject", "reject"])
        self._frames(pid, sid, ["block"], ["reject"], decided=T_BEFORE)          # the person decided first → not counted
        out = trainee.score_project(self.conn, pid)
        self.assertEqual(out["qc_team"]["scored"], 2)
        self.assertEqual(out["qc_team"]["human_first"], 1)
        rows = self.conn.execute("SELECT decision, truth, truth_source, match FROM trainee_log ORDER BY id").fetchall()
        self.assertEqual([tuple(r) for r in rows],
                         [("block", "reject", "review", 1), ("pass", "reject", "review", 0), ("block", None, "human_first", None)])
        # an AI reviewer's decision is never the truth
        jid = self.p.create_job(sid, "image_gen")
        trainee.record(self.conn, "qc_team", pid, f"job:{jid}", "pass", job_id=jid, at=T0)
        self.conn.execute("INSERT INTO review_log (job_id, reviewer_type, decision, decided_at) VALUES (?,?,?,?)",
                          (jid, "ai_agent", "approve", T_AFTER))
        trainee.score_project(self.conn, pid)
        self.assertIsNone(self.conn.execute("SELECT truth FROM trainee_log WHERE job_id=?", (jid,)).fetchone()[0])

    def test_bulk_approval_is_reported_apart(self):
        pid, sid = self._project()
        self._frames(pid, sid, ["pass"] * 5, ["approve"] * 5)                     # 5 approvals in the same second = "Duyệt tất cả"
        trainee.score_project(self.conn, pid)
        srcs = {r[0] for r in self.conn.execute("SELECT truth_source FROM trainee_log")}
        self.assertEqual(srcs, {"gate_bulk"})
        self.assertEqual(trainee.agreement(self.conn, "qc_team")["n_bulk"], 5)

    def test_label_card(self):
        pid, _ = self._project()
        rid = trainee.record(self.conn, "end_frames", pid, "end:248", "need_end", at=T0)
        trainee.label(self.conn, rid, False)                                     # 👎: the clip did not need an end frame
        row = self.conn.execute("SELECT truth, truth_source, match FROM trainee_log WHERE id=?", (rid,)).fetchone()
        self.assertEqual(tuple(row), ("no_end", "card", 0))
        trainee.label(self.conn, rid, True)
        self.assertEqual(self.conn.execute("SELECT match FROM trainee_log WHERE id=?", (rid,)).fetchone()[0], 1)

    def test_fixture_22_always_block_is_not_ready(self):
        """#22 Khủng Long Đỏ: 37 frames, the person rejected 28 / approved 9. 'Always block' scores 76 % — never 'đủ chuẩn'."""
        for name in ("#22 Khủng Long Đỏ", "#23"):
            pid, sid = self._project(name)
            self._frames(pid, sid, ["block"] * 37, ["reject"] * 28 + ["approve"] * 9, decided=T_AFTER)
            trainee.score_project(self.conn, pid)
        a = trainee.agreement(self.conn, "qc_team")
        self.assertFalse(a["ready"])
        self.assertAlmostEqual(a["rate"], 28 / 37, places=3)
        self.assertAlmostEqual(a["balanced"], 0.5, places=3)
        self.assertEqual(a["too_strict"], 18)                                    # blocked frames the person approved
        self.assertEqual(a["too_loose"], 0)
        self.assertTrue(any("80" in m or "cân bằng" in m for m in a["missing"]))

    def test_always_block_at_85_percent_still_not_ready(self):
        """Above 80 % only because most frames are bad: balanced 50 %, no better than the majority label."""
        for name in ("A", "B"):
            pid, sid = self._project(name)
            self._frames(pid, sid, ["block"] * 20, ["reject"] * 17 + ["approve"] * 3, decided=T_AFTER)
            trainee.score_project(self.conn, pid)
        a = trainee.agreement(self.conn, "qc_team")
        self.assertGreaterEqual(a["rate"], 0.8)
        self.assertFalse(a["ready"])
        self.assertTrue(any("nhãn đông nhất" in m for m in a["missing"]))
        self.assertTrue(any("cân bằng" in m for m in a["missing"]))

    def test_a_good_role_is_ready_but_never_verified(self):
        from core import features
        for name in ("A", "B"):
            pid, sid = self._project(name)
            dec = ["block"] * 8 + ["pass"] * 1 + ["pass"] * 8 + ["block"] * 1      # 16/18 right per project, both classes
            truth = ["reject"] * 9 + ["approve"] * 9
            self._frames(pid, sid, dec, truth, decided=T_AFTER)
            trainee.score_project(self.conn, pid)
        a = trainee.agreement(self.conn, "qc_team")
        self.assertTrue(a["ready"], a["missing"])
        self.assertEqual(len(a["per_project"]), 2)
        self.assertFalse(features.FEATURES["qc_team"]["verified"])               # ready only says "🎓 đủ chuẩn — chờ duyệt"

    def test_one_project_is_not_enough(self):
        pid, sid = self._project()
        self._frames(pid, sid, ["block"] * 10 + ["pass"] * 10, ["reject"] * 10 + ["approve"] * 10, decided=T_AFTER)
        trainee.score_project(self.conn, pid)
        a = trainee.agreement(self.conn, "qc_team")
        self.assertFalse(a["ready"])
        self.assertTrue(any("2 dự án" in m for m in a["missing"]))

    def test_storyboard_needs_look_trust(self):
        for name in ("A", "B"):
            pid, _ = self._project(name)
            for i in range(3):
                rid = trainee.record(self.conn, "storyboard_auto_trust", pid, f"gate:storyboard:{name}{i}", "skip_gate", at=T0)
                trainee.label(self.conn, rid, True, source="gate_fingerprint")
            rid = trainee.record(self.conn, "storyboard_auto_trust", pid, f"gate:storyboard:{name}h", "hold_gate", at=T0)
            trainee.label(self.conn, rid, True, source="gate_fingerprint")
        self.assertFalse(trainee.agreement(self.conn, "storyboard_auto_trust")["ready"])
        self.assertTrue(trainee.agreement(self.conn, "storyboard_auto_trust", look_trusted=True)["ready"])


class StoryboardTrustTraineeTests(unittest.TestCase):
    """B3 học việc 08/10: storyboard_auto_trust 🎓 — records skip_gate / hold_gate once per storyboard, the gate stays for the person."""

    def setUp(self):
        from tests._flags import flags_trainee
        flags_trainee(self, "storyboard_auto_trust")
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t", operating_mode="human_qc", threshold=0.5)

    def _run(self, trusted, flags):
        from core import autopilot
        with mock.patch("core.effectiveness.look_trust", return_value={"trusted": trusted, "agreement": 0.9, "pairs": 30}), \
                mock.patch("core.storyboard_gate.flags", return_value=flags), \
                mock.patch("core.storyboard_gate.fingerprint", return_value=[11, 12]), \
                mock.patch("core.autopilot.set_gates") as gates:
            out = autopilot._qc_trusted(self.p, self.pid, None)
        self.assertFalse(out)                                       # never skips the gate
        gates.assert_not_called()

    def test_skip_then_once_per_fingerprint(self):
        self._run(True, {"outliers": []})
        self._run(True, {"outliers": []})
        rows = self.p.conn.execute("SELECT decision, subject FROM trainee_log WHERE feature='storyboard_auto_trust'").fetchall()
        self.assertEqual([r["decision"] for r in rows], ["skip_gate"])
        self.assertTrue(rows[0]["subject"].startswith("gate:storyboard:"))

    def test_hold_when_a_flag_is_raised(self):
        self._run(True, {"outliers": [3]})
        self.assertEqual(self.p.conn.execute("SELECT decision FROM trainee_log").fetchone()[0], "hold_gate")


if __name__ == "__main__":
    unittest.main()
