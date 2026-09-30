"""S10.4 (người dùng 30/09): a shot where a character uses an active skill goes to Seedance 2.5 in reference mode — the approved picture
as the first frame (by role sentence), one identity picture per person, the official skill video cut(s) — with the asset roles written to
the official template and the effect not described again (test T1 30/09)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import llm_runner, model_router, shots, skill_dossier
from tests.test_seedance_refs import real_png
from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project

ON = {"FEATURE_SKILL_DOSSIER": "1", "FEATURE_SEEDANCE_REF_GROUPS": "1"}


class SkillRouteTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, ON)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        self.data = tempfile.mkdtemp()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        rows = shots.shots_of(self.p, self.pid)
        self.sid = rows[0]["id"]
        d = dict(rows[0]["data"], characters=["KENTA"], skill_phase="KENTA:wind_fly", size="MS", sequence=99)
        for k in ("dialogue", "lip_sync", "video_route", "plate_mode"):
            d.pop(k, None)
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), self.sid))
        self.p.conn.commit()

    def test_a_skill_shot_goes_to_seedance_2_5_even_in_cheap_test_mode(self):
        choice = model_router.scene_choice(self.p.conn, self.sid)
        self.assertEqual((choice["model"], choice.get("skill")), ("seedance-2.5", True))
        self.assertIn("KENTA", choice["reason"])
        self.p.conn.execute("UPDATE projects SET test_quality=1 WHERE id=?", (self.pid,))
        self.assertEqual(model_router.scene_choice(self.p.conn, self.sid)["model"], "seedance-2.5")
        with mock.patch.dict(os.environ, {"FEATURE_SKILL_DOSSIER": "0"}):
            self.assertIsNone(model_router.scene_choice(self.p.conn, self.sid).get("skill"))

    def test_a_phase_without_a_video_cut_keeps_the_old_way(self):
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.sid,)).fetchone()["data"])
        self.assertIsNone(skill_dossier.route_reason(dict(d, skill_phase="KENTA:move_vortex")))   # the dash has no cut: words carry it

    def test_the_send_has_the_first_frame_the_people_and_the_video_with_roles(self):
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        real_png(shots.approved_image_path(self.p.conn, self.data, self.pid, self.sid))
        vr = VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data)
        job = self.p.job(self.p.create_job(self.sid, "video_gen"))
        kw = vr._submit_kwargs(job)
        self.assertEqual(kw["reference_only"][0], shots.approved_image_path(self.p.conn, self.data, self.pid, self.sid))
        self.assertEqual(len(kw["reference_video"]), 1)
        self.assertTrue(kw["reference_video"][0]["path"].endswith(".mp4"))
        args = vr._submit_args(job)
        self.assertEqual(args[4], "seedance-2.5")
        prompt = args[1]
        self.assertIn("@Image 1 is the first frame.", prompt)
        self.assertIn("@Video 1 is used only for KENTA's skill effect", prompt)
        self.assertIn("[Event] ", prompt)
        self.assertNotIn("Skill effect exactly as in the game", prompt)          # the video carries it — not described again
        self.assertIsNone(vr._sends_group(job))

    def test_two_skills_in_one_shot_give_two_videos_in_order(self):
        data = {"characters": ["KENTA", "ORION"], "skill_phase": "KENTA:wind_fly; ORION:drain"}
        hits = skill_dossier.shot_skills(data)
        self.assertEqual([h["dossier"]["character"] for h in hits], ["KENTA", "ORION"])
        block = skill_dossier.reference_block(hits, ["KENTA", "ORION"])
        self.assertIn("@Image 2 is KENTA", block)
        self.assertIn("@Image 3 is ORION", block)
        self.assertIn("@Video 2 is used only for ORION's skill effect", block)
        self.assertIn("never swap", block)
        self.assertIn("ORION's skill in this shot: drain.", block)


if __name__ == "__main__":
    unittest.main()
