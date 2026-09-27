"""Flag seedance_ref_groups (người dùng chốt 2026-09-27, docs/PHAN_TICH_GOP_SHOT_2026-09-27.md mục 6): consecutive shots of a continuity
group are made in ONE Seedance generation from their own marked storyboard pictures (reference only, no start frame); a refusal moves
the shots to Seedance per shot, then to Kling — each step changes the input once (luật 6)."""
import json
import os
import subprocess
import tempfile
import unittest

from core import end_frames, llm_runner, model_router, seedance_refs, shots
from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project


def real_png(path, color=(40, 90, 40)):
    from PIL import Image
    Image.new("RGB", (180, 320), color).save(path)


class SeedanceRefTests(unittest.TestCase):
    def setUp(self):
        os.environ["FEATURE_SEEDANCE_REF_GROUPS"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_SEEDANCE_REF_GROUPS", None)
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        self.data = tempfile.mkdtemp()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        rows = shots.shots_of(self.p, self.pid)
        first = rows[0]["data"]["story_scene"]
        self.scene = [r for r in rows if r["data"]["story_scene"] == first]
        self.assertGreaterEqual(len(self.scene), 2, "the mock plan needs 2+ shots in its first scene")
        for r in self.scene:                                     # one continuity group, short shots
            d = dict(r["data"], sequence=1, duration_s=2.0)
            d.pop("plate_mode", None)
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), r["id"]))
        self.p.conn.commit()
        self.ids = [r["id"] for r in self.scene][:seedance_refs.GROUP_MAX_SHOTS]

    def _ready(self):
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        for sid in self.ids:                                     # marking reads real pictures
            real_png(shots.approved_image_path(self.p.conn, self.data, self.pid, sid))
        return VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data)

    def test_a_group_every_shot_draws_its_own_picture(self):
        group = shots.group_of(self.p.conn, self.ids[1])
        self.assertEqual([r["id"] for r in group], self.ids)
        for sid in self.ids:
            self.assertTrue(shots.needs_own_image(self.p.conn, sid))
            self.assertEqual(shots.image_scene(self.p.conn, sid), sid)
        choice = model_router.scene_choice(self.p.conn, self.ids[0])
        self.assertIn("seedance", choice["model"])

    def test_no_end_frame_is_drawn_for_a_reference_shot(self):
        data = dict(self.scene[0]["data"], end_state="cầm súng lên")
        self.assertFalse(end_frames.needed(data, "per_shot"))
        self.assertTrue(end_frames.needed(dict(data, video_route="kling"), "per_shot"))

    def test_the_leader_sends_marked_pictures_and_a_shot_by_shot_prompt(self):
        vr = self._ready()
        leader = self.p.job(self.p.create_job(self.ids[0], "video_gen"))
        follower = self.p.job(self.p.create_job(self.ids[1], "video_gen"))
        self.assertTrue(vr._wait(follower))
        args = vr._submit_args(leader)
        self.assertIn("seedance", args[4])
        self.assertIn("Image 1 is the storyboard frame of Shot 1", args[1])
        self.assertIn(f"Shot {len(self.ids)} (", args[1])
        self.assertGreaterEqual(args[3], seedance_refs.SEEDANCE_MIN)
        kw = vr._submit_kwargs(leader)
        self.assertNotIn("last_frame", kw)
        self.assertNotIn("multi_prompt", kw)
        self.assertGreaterEqual(len(kw["reference_only"]), len(self.ids))
        self.assertTrue(all(p.endswith("_marked.png") and os.path.exists(p) for p in kw["reference_only"]))
        stamp = json.loads(vr._stamp(leader, args)["sent_group"])
        self.assertTrue(all(g["refs"] for g in stamp))

    def test_refusal_steps_group_then_single_then_kling(self):
        from core.adapters.clipai import REAL_PERSON
        vr = self._ready()
        leader = self.p.job(self.p.create_job(self.ids[0], "video_gen"))
        self.p.conn.execute("UPDATE jobs SET model='seedance-fast' WHERE id=?", (leader["id"],))
        self.assertTrue(vr._on_refused(self.p.job(leader["id"]), REAL_PERSON, "may contain real person"))
        self.assertIsNone(shots.group_of(self.p.conn, self.ids[0]))                     # now one shot each, still Seedance
        self.assertIn("seedance", model_router.scene_choice(self.p.conn, self.ids[0])["model"])
        kw = vr._submit_kwargs(self.p.job(leader["id"]))
        self.assertEqual(len([p for p in kw["reference_only"] if "job_" in os.path.basename(p)]), 1)
        self.assertTrue(vr._on_refused(self.p.job(leader["id"]), REAL_PERSON, "may contain real person"))
        self.assertEqual(model_router.scene_choice(self.p.conn, self.ids[0])["model"], "kling")
        self.assertFalse(vr._refs(self.p.job(leader["id"])))                             # Kling: from the start frame again

    def test_the_estimate_pays_one_clip_per_group(self):
        rows = {r["scene_id"]: r for r in model_router.plan(self.p.conn, self.pid)}
        n = len(self.ids)
        self.assertEqual(rows[self.ids[0]]["billed_seconds"], seedance_refs.seconds([2.0] * n))   # the group's seconds, ≥ 4
        for sid in self.ids[1:]:
            self.assertEqual(rows[sid]["billed_seconds"], 0.0)
            self.assertIn("trong clip nhóm", rows[sid]["reason"])

    def test_motion_prompts_of_reference_shots_are_written_by_code(self):
        from core.providers import MockImageProvider  # noqa: F401 - the images are approved by _ready
        self._ready()
        self.p.conn.execute("DELETE FROM motion_prompts WHERE scene_id IN (%s)" % ",".join(map(str, self.ids)))
        self.p.conn.commit()
        n = seedance_refs.code_motion(self.p, self.pid)
        self.assertGreaterEqual(n, len(self.ids))
        for sid in self.ids:
            mp = self.p.conn.execute("SELECT motion_prompt, state FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()
            self.assertEqual(mp["state"], "approved")
            self.assertIn("angle, camera", mp["motion_prompt"])
        self.assertEqual(seedance_refs.code_motion(self.p, self.pid), 0)            # once

    def test_off_by_default(self):
        os.environ.pop("FEATURE_SEEDANCE_REF_GROUPS", None)
        self.assertIsNone(shots.group_of(self.p.conn, self.ids[1]))
        self.assertFalse(seedance_refs.uses_refs(self.p.conn, self.ids[0]))


class SplitTests(unittest.TestCase):
    def test_cut_at_the_cuts_the_model_made(self):
        from core import ffmpeg_studio
        try:
            ff = ffmpeg_studio.find_ffmpeg()
        except ffmpeg_studio.FFmpegNotFound:
            self.skipTest("no ffmpeg")
        d = tempfile.mkdtemp()
        clip = os.path.join(d, "01.mp4")
        # three "shots" of 3,0 / 1,5 / 2,5 s (the plan said 2 / 2 / 2): the files follow the real cuts, not the plan
        subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=96x160:d=3", "-f", "lavfi", "-i",
                        "color=c=blue:s=96x160:d=1.5", "-f", "lavfi", "-i", "color=c=green:s=96x160:d=2.5", "-filter_complex",
                        "[0][1][2]concat=n=3:v=1:a=0", "-r", "24", "-c:v", "libx264", "-pix_fmt", "yuv420p", clip], check=True)
        group = [{"id": k, "idx": k, "data": {"duration_s": 2.0}} for k in (1, 2, 3)]
        res = seedance_refs.split(clip, group, [clip] + [os.path.join(d, f"0{k}.mp4") for k in (2, 3)], ff)
        self.assertEqual(res["by"], "detected")
        lengths = [ffmpeg_studio.probe_duration(p) for p in res["paths"]]
        for got, want in zip(lengths, (3.0, 1.5, 2.5)):
            self.assertAlmostEqual(got, want, delta=0.15)

    def test_prompt_names_every_picture(self):
        text = seedance_refs.prompt([("Kenta chạy", 2.0), ("Kelly quay lại", 1.5)], [("KENTA", "k.png")])
        self.assertIn("Image 2 is the storyboard frame of Shot 2", text)
        self.assertIn("Image 3 is KENTA: identity only", text)
        self.assertIn("Shot 2 (2.0–3.5 s)", text)
        self.assertIn("annotations, never part of the video", text)


if __name__ == "__main__":
    unittest.main()
