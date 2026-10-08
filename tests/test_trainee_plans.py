"""B4 🎓 học việc (08/10): camera_setups / continuous_takes / end_frames only WRITE their plan (trainee_log), 0 USD, no effect —
the Director prompt has no "Vị trí máy", shots.group_of is unchanged, no end frame is queued/drawn, the estimate counts none."""
import json
import tempfile
import unittest
from unittest import mock

from core import autopilot, cost, end_frames, features, llm_runner, prompts, shots, trainee_plans
from tests.test_end_frames import _shot_with_end_state
from tests.test_v3 import _approve_all_images, kenta_project

ROLES = ("camera_setups", "continuous_takes", "end_frames")


def _trainee(tc, *names):
    features.save_settings(flags={n: None for n in names}, modes={n: "trainee" for n in names})
    tc.addCleanup(features.save_settings, modes={n: None for n in names})


def _log(conn, pid, feature):
    return conn.execute("SELECT subject, decision, would_do FROM trainee_log WHERE feature=? AND project_id=? ORDER BY id",
                        (feature, pid)).fetchall()


class TraineePlanTests(unittest.TestCase):
    def setUp(self):
        _trainee(self, *ROLES)
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        rows = shots.shots_of(self.p, self.pid)
        first = rows[0]["data"]["story_scene"]
        self.scene = [r for r in rows if r["data"]["story_scene"] == first]
        self.assertGreaterEqual(len(self.scene), 3)
        for r, letter in zip(self.scene, "AAB"):
            d = dict(r["data"], camera_setup=letter, continuous_with_next=False)
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), r["id"]))
        self.p.conn.commit()
        self.sid = _shot_with_end_state(self.p, self.pid)
        self.data = tempfile.mkdtemp()

    def test_director_prompt_has_no_camera_setup_rule(self):
        rule = "**Vị trí máy**: gán `camera_setup`"            # the H5 line of prompts.duration_block (knowledge/dp.md says it too)
        self.assertNotIn(rule, prompts.build_director_bundle(self.p, self.pid))
        from tests._flags import flags_on_ctx
        features.save_settings(modes={"camera_setups": None})
        with flags_on_ctx("camera_setups"):
            self.assertIn(rule, prompts.build_director_bundle(self.p, self.pid))

    def test_nothing_before_every_picture_is_approved(self):
        self.assertEqual(trainee_plans.record_plans(self.p.conn, self.pid), {})
        self.assertEqual(_log(self.p.conn, self.pid, "camera_setups"), [])

    def test_plans_recorded_group_of_unchanged_no_end_frame_drawn(self):
        before = {r["id"]: shots.group_of(self.p.conn, r["id"]) for r in self.scene}
        _approve_all_images(self.p, self.pid, self.data)
        autopilot._trainee_plans(self.p, self.pid)
        self.assertEqual({r["id"]: shots.group_of(self.p.conn, r["id"]) for r in self.scene}, before)
        self.assertTrue(all(g is None for g in before.values()))
        story = self.scene[0]["data"]["story_scene"]
        groups = _log(self.p.conn, self.pid, "camera_setups")
        self.assertIn(f"group:{story}:A", [g["subject"] for g in groups])
        a = next(g for g in groups if g["subject"] == f"group:{story}:A")
        self.assertEqual(a["decision"], "group")
        would = json.loads(a["would_do"])
        self.assertEqual(would["scene_ids"], [self.scene[0]["id"], self.scene[1]["id"]])
        self.assertIn("saved_s", would)
        stretches = _log(self.p.conn, self.pid, "continuous_takes")
        self.assertTrue(any(s["subject"].startswith(f"stretch:{story}:") and s["decision"] == "stretch" for s in stretches))
        ends = _log(self.p.conn, self.pid, "end_frames")
        self.assertIn(f"end:{self.sid}", [e["subject"] for e in ends])
        self.assertEqual(json.loads(next(e for e in ends if e["subject"] == f"end:{self.sid}")["would_do"])["route"], "first_last")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM end_frames").fetchone()[0], 0)      # nothing queued / drawn
        self.assertEqual(cost.pending_end_frames(self.p, self.pid), 0)
        # once per subject: a second run writes nothing new; a changed plan updates its row
        n = self.p.conn.execute("SELECT COUNT(*) FROM trainee_log").fetchone()[0]
        res = trainee_plans.record_plans(self.p.conn, self.pid)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM trainee_log").fetchone()[0], n)
        self.assertTrue(all(c["new"] == 0 and c["updated"] == 0 for c in res.values()))
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid,)).fetchone()["data"])
        d["end_state"] = "Kenta stands up again"
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), self.sid))
        self.p.conn.commit()
        res = trainee_plans.record_plans(self.p.conn, self.pid)
        self.assertEqual(res["end_frames"]["updated"], 1)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM trainee_log").fetchone()[0], n)

    def test_need_end_recorded_even_with_seedance_ref_groups(self):
        from core import seedance_refs
        _approve_all_images(self.p, self.pid, self.data)
        with mock.patch.object(features, "on", side_effect=lambda n: n == "seedance_ref_groups"), \
                mock.patch.object(seedance_refs, "eligible", return_value=True):
            self.assertFalse(end_frames.needed({"end_state": "he falls"}, "per_shot"))
            self.assertTrue(end_frames.needed({"end_state": "he falls"}, "per_shot", ignore_route=True))
            trainee_plans.record_plans(self.p.conn, self.pid)
        ends = _log(self.p.conn, self.pid, "end_frames")
        row = next(e for e in ends if e["subject"] == f"end:{self.sid}")
        self.assertEqual(row["decision"], "need_end")
        self.assertEqual(json.loads(row["would_do"])["route"], "seedance_ref")
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM end_frames").fetchone()[0], 0)


class GuessedSetupTests(unittest.TestCase):
    def test_same_scene_size_angle_people_next_to_each_other(self):
        rows = [{"id": i, "idx": i, "data": {"shot_no": i, "story_scene": 1, "size": sz, "angle": "eye", "characters": ["KENTA"],
                                                 "duration_s": 3}} for i, sz in enumerate(["MS", "MS", "CU", "MS"], 1)]
        with mock.patch.object(shots, "_rows", return_value=rows):
            labelled = trainee_plans._labelled_rows(None, 1)
        self.assertEqual([r["data"]["camera_setup"] for r in labelled], ["H1", "H1", "H2", "H3"])
        self.assertEqual([[r["id"] for r in g] for g in shots.setup_groups_of(labelled)], [[1, 2]])


if __name__ == "__main__":
    unittest.main()
