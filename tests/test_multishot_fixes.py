"""GĐ-E2 (docs/KE_HOACH_TONG_2026-09-24.md): Kling multi-shot faults found in the real GĐ6 run — a group whose first picture lacks a
later shot's people (F4/R4), a later shot that could not be remade ("missing inputs", M1), a per-shot model override splitting a group
and Claude told the single-clip limits (M9), and a paid clip cut by a re-planned group (M10); plus the video retry carries the fix (W3)."""
import json
import unittest

from core import llm_io, llm_runner, model_router, prompts, shots
from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project


def cast(p, sid):
    return json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"] or "{}").get("characters") or []


class MultishotTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.p, self.pid = kenta_project(shot_mode="multishot")
        self.data = tempfile.mkdtemp()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())

    def test_every_later_shot_of_a_group_only_has_people_of_the_first_picture(self):
        for group in shots.multishot_groups(self.p.conn, self.pid):
            first = set(cast(self.p, group[0]["id"]))
            for r in group[1:]:
                self.assertLessEqual(set(cast(self.p, r["id"])), first, f"shot {r['idx']} has people missing from the group picture")

    def test_a_shot_with_a_new_person_starts_its_own_group(self):
        group = next(g for g in shots.multishot_groups(self.p.conn, self.pid) if len(g) > 1)
        later = group[1]
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (later["id"],)).fetchone()["data"])
        data["characters"] = list(data.get("characters") or []) + ["NGƯỜI LẠ"]
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), later["id"]))
        self.p.conn.commit()
        self.assertEqual(shots.multishot_group_of(self.p.conn, later["id"])[0]["id"], later["id"])

    def test_a_group_ignores_a_per_shot_override_and_claude_gets_the_kling_limits(self):
        group = next(g for g in shots.multishot_groups(self.p.conn, self.pid) if len(g) > 1)
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        model_router.set_override(self.p.conn, group[1]["id"], "seedance-2.5")
        choice = model_router.scene_choice(self.p.conn, group[1]["id"])
        self.assertEqual(choice["model"], "kling")
        self.assertIn("không áp dụng trong nhóm", choice["reason"])
        bundle = prompts.build_motion_bundle(self.p, self.pid)
        self.assertIn('"prompt_max_chars": 512', bundle)

    def test_a_later_shot_can_be_remade_from_its_group_picture(self):
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        group = next(g for g in shots.multishot_groups(self.p.conn, self.pid) if len(g) > 1)
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        vr = VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data)
        jid = self.p.create_job(group[1]["id"], "video_gen")
        self.assertIsNotNone(vr._submit_args(self.p.job(jid)))                  # M1: used to be "missing inputs"

    def test_a_video_retry_sends_the_qc_fix_with_the_motion_prompt(self):
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        sid = shots.multishot_groups(self.p.conn, self.pid)[0][0]["id"]
        vr = VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data)
        jid = self.p.create_job(sid, "video_gen")
        self.p.conn.execute("UPDATE jobs SET retry_reason='Keep Kenta on the left.' WHERE id=?", (jid,))
        self.p.conn.commit()
        self.assertIn("Fix: Keep Kenta on the left.", vr._submit_args(self.p.job(jid))[1])    # W3: never the very same input again

    def test_the_group_is_stored_when_sent(self):
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        from core import batch
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        vr = VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data)
        batch.queue_videos(self.p, self.pid, self.data)
        vr.submit_pending(self.pid)
        sent = [json.loads(r["sent_group"]) for r in self.p.conn.execute("SELECT sent_group FROM jobs WHERE sent_group IS NOT NULL")]
        self.assertTrue(sent)
        self.assertTrue(all(len(g) > 1 and all("duration_s" in x for x in g) for g in sent))   # M10


if __name__ == "__main__":
    unittest.main()
