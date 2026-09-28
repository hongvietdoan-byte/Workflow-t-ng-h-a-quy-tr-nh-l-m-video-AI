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
        self.assertIn(f"Shot {len(self.ids)}: ", args[1])
        self.assertGreaterEqual(args[3], seedance_refs.SEEDANCE_MIN)
        kw = vr._submit_kwargs(leader)
        self.assertNotIn("last_frame", kw)
        self.assertNotIn("multi_prompt", kw)
        self.assertGreaterEqual(len(kw["reference_only"]), len(self.ids))
        self.assertTrue(all(p.endswith("_marked.png") and os.path.exists(p) for p in kw["reference_only"]))
        stamp = json.loads(vr._stamp(leader, args)["sent_group"])
        self.assertTrue(all(g["refs"] for g in stamp))

    def test_consecutive_shots_remade_later_go_as_one_group_clip_not_one_by_one(self):
        """#8 2026-09-28: 19 shots remade for their voices went out one by one (>= 4 s billed each) and two lost the identity."""
        if len(self.ids) < 3:
            self.skipTest("needs a group of 3")
        vr = self._ready()
        done = self.p.create_job(self.ids[0], "video_gen")         # the first shot keeps its clip
        self.p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (done,))
        for sid in self.ids[1:]:                                   # the others had clips, now stale → remade
            old = self.p.create_job(sid, "video_gen")
            self.p.conn.execute("UPDATE jobs SET state='rejected' WHERE id=?", (old,))
        self.p.conn.commit()
        jobs = [self.p.job(self.p.create_job(sid, "video_gen")) for sid in self.ids[1:]]
        run = vr._sends_group(jobs[0])
        self.assertEqual([r["id"] for r in run], self.ids[1:])       # the second shot sends for the rest of the group
        self.assertFalse(vr._wait(jobs[0]))
        self.assertTrue(all(vr._wait(j) for j in jobs[1:]))          # the others wait for their part
        args = vr._submit_args(jobs[0])
        self.assertIn(f"Shot {len(self.ids) - 1}: ", args[1])          # Seedance 2.0: shot numbers, no time marks (S4.8)
        stamp = vr._stamp(jobs[0], args)
        self.p.conn.execute("UPDATE jobs SET state='running', sent_group=? WHERE id=?", (stamp["sent_group"], jobs[0]["id"]))
        self.p.conn.commit()
        self.assertTrue(vr._wait(self.p.job(jobs[1]["id"])))        # carried by the group clip in flight, not sent alone
        rows = {r["scene_id"]: r for r in model_router.plan(self.p.conn, self.pid)}
        self.p.conn.execute("UPDATE jobs SET state='queued', sent_group=NULL WHERE id=?", (jobs[0]["id"],))
        self.p.conn.commit()
        rows = {r["scene_id"]: r for r in model_router.plan(self.p.conn, self.pid)}
        self.assertGreater(rows[self.ids[1]]["cost"], 0)             # the run is ONE clip, priced on its first shot…
        self.assertTrue(all(rows[sid]["cost"] == 0 for sid in self.ids[2:]))   # …not one clip per shot

    def test_a_lone_reference_shot_keeps_its_whole_clip(self):
        """28/09 S5·1: the prompt spread the fall over the 4 s clip, the cut to its 2 s plan lost the fall."""
        from unittest import mock
        vr = self._ready()
        job = self.p.job(self.p.create_job(self.ids[-1], "video_gen"))
        with mock.patch.object(vr, "_sends_group", return_value=None), mock.patch.object(vr, "_refs", return_value=True),                 mock.patch("core.shots.trim_clip") as trim, mock.patch.object(vr, "_plate_video"):
            try:
                vr._after_download(job, os.path.join(self.data, "x.mp4"))
            except Exception:  # noqa: BLE001 - only whether it cut matters here
                pass
        trim.assert_not_called()

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


class ReviewFixTests(unittest.TestCase):
    """Independent review 2026-09-27 of the code-built motion prompts (group prompts past 4,000 characters, Vietnamese in 28/33 shots,
    marks ending before the clip, 'no sound' with a voice, pictures not matching the table)."""
    SHOT = {"size": "MS", "angle": "eye", "camera_move": "static", "characters": ["KELLY"], "duration_s": 2.0,
            "image_prompt": "Free Fire in-game 3D render, stylized proportions, KELLY in her yellow tracksuit …",
            "action": "Kelly quay người bước đi", "performance": {"face": "hurt", "body": "turns away"},
            "dialogue": [{"speaker": "KELLY", "text": "Em hiểu rồi"}]}

    def test_the_motion_says_what_happens_in_english_not_the_picture(self):
        d = dict(self.SHOT, motion_en={"action": "Kelly turns and walks away", "end_state": "her back to the camera"})
        text = seedance_refs.shot_motion(d)
        self.assertIn("Kelly turns and walks away", text)
        self.assertIn("It ends with her back to the camera", text)
        self.assertNotIn("in-game 3D render", text)                     # the frame carries the picture, the look is said once
        self.assertFalse(seedance_refs.has_vietnamese(text))
        self.assertTrue(seedance_refs.has_vietnamese(seedance_refs.shot_motion(self.SHOT)))   # untranslated: caught by the lint
        self.assertNotIn("no sound", seedance_refs.shot_motion(d, voice=True))

    def test_the_marks_are_stretched_to_the_clip_really_made(self):
        text = seedance_refs.prompt([("a", 1.0), ("b", 1.0)], [], clip_seconds=4, model="seedance-2.5")
        self.assertIn("Shot 2 (2–4 s)", text)

    def test_what_can_be_seen_wrong_before_paying(self):
        long = "x" * 4100
        self.assertTrue(any("4000" in p for p in seedance_refs.lint_group(long, 2, 3, 3, [2, 2], False)))
        self.assertTrue(any("tiếng Việt" in p for p in seedance_refs.lint_group("Kelly quay người", 1, 2, 2, [2], False)))
        self.assertTrue(any("ảnh" in p for p in seedance_refs.lint_group("ok", 3, 4, 5, [2, 2, 2], False)))
        self.assertTrue(any("no sound" in p for p in seedance_refs.lint_group("KELLY speaks (mouth moving, no sound).", 1, 2, 2, [3], True)))
        self.assertEqual(seedance_refs.lint_group("fine", 2, 3, 3, [2, 2], False), [])
        self.assertEqual(seedance_refs.short_shots([0.5, 2.0]), [1])

    def test_a_group_is_closed_before_its_prompt_is_too_long(self):
        os.environ["FEATURE_SEEDANCE_REF_GROUPS"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_SEEDANCE_REF_GROUPS", None)
        p, pid = kenta_project(shot_mode="per_shot")
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        rows = shots.shots_of(p, pid)
        first = rows[0]["data"]["story_scene"]
        for r in rows:
            if r["data"]["story_scene"] == first:
                d = dict(r["data"], sequence=1, duration_s=2.0, performance={"face": "y" * 900})
                d.pop("plate_mode", None)
                p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), r["id"]))
        p.conn.commit()
        for g in seedance_refs.groups(p.conn, pid):
            self.assertLessEqual(seedance_refs._estimated_len(g), seedance_refs.GROUP_PROMPT_BUDGET)

    def test_one_call_translates_only_the_vietnamese_fields(self):
        from core import claude_tasks
        p, pid = kenta_project(shot_mode="per_shot")
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        sid = shots.shots_of(p, pid)[0]["id"]
        idx = p.conn.execute("SELECT idx FROM scenes WHERE id=?", (sid,)).fetchone()["idx"]
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(dict(self.SHOT, story_scene=1, shot_no=1), ensure_ascii=False), sid))
        p.conn.commit()
        for other in p.conn.execute("SELECT id, data FROM scenes WHERE project_id=? AND id!=?", (pid, sid)).fetchall():
            d = json.loads(other["data"] or "{}")
            d.pop("action", None)
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), other["id"]))
        p.conn.commit()
        answers = [{str(idx): {"action": "Kelly quay đi"}}, {str(idx): {"action": "Kelly turns and walks away"}}]

        class C:
            name = "fake"

            def complete(self, prompt, images=()):
                return llm_runner.LlmReply(json.dumps(answers.pop(0)), 10, 5)
        self.assertEqual(claude_tasks.translate_motion_fields(p, pid, C()), 1)   # the Vietnamese answer is asked again
        d = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])
        self.assertEqual(d["motion_en"]["action"], "Kelly turns and walks away")
        self.assertEqual(d["action"], "Kelly quay người bước đi")                 # the Director's own field is kept
        self.assertEqual(claude_tasks.translate_motion_fields(p, pid, C()), 0)   # 28/09: a resume does not pay the same translation again
        d["action"] = "Kelly quay lại nhìn Kenta"                                   # the Vietnamese changed → translated again
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), sid))
        answers.append({str(p.conn.execute("SELECT idx FROM scenes WHERE id=?", (sid,)).fetchone()[0]): {"action": "Kelly turns back to Kenta"}})
        self.assertEqual(claude_tasks.translate_motion_fields(p, pid, C()), 1)


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
        self.assertIn("Shot 2: Kelly quay lại.", text)                    # no time marks: the model is not known to read them
        self.assertIn("annotations, never part of the video", text)


class ShotFloorTests(unittest.TestCase):
    """#8 2026-09-28: 0.46-1.4 s shots in group clips — the action was skipped (QC: 'Kelly never turns away', 'Maxim does not collapse')."""

    def test_a_short_shot_gets_the_group_floor_and_a_big_action_more(self):
        from core import seedance_refs as sr
        self.assertEqual(sr.floored({"action": "Kelly nhìn Kenta"}, 0.46), sr.MIN_GROUP_SHOT)
        self.assertEqual(sr.floored({"motion_en": {"action": "Kelly turns and walks away"}}, 1.1), sr.MIN_ACTION_SHOT)
        self.assertEqual(sr.floored({"action": "x"}, 3.2), 3.2)                             # a long shot keeps its length
        text = sr.prompt([("a", sr.floored({}, 0.4)), ("b", 2.0)], [], model="seedance-2.5")
        self.assertIn("Shot 1 (0–2 s)", text)

    def test_the_shot_text_carries_the_framing_in_english_only(self):
        from core import seedance_refs as sr
        d = {"size": "MS", "angle": "ots", "blocking": "Same over-the-shoulder composition as previous shot: KENTA's shoulder blurred in right "
             "foreground, KELLY center-left, cold blue shadow lighting unchanged", "action": "x"}
        t = sr.shot_motion(d)
        self.assertIn("framing KENTA's shoulder blurred in right foreground", t)
        self.assertNotIn("Same over-the-shoulder", t)
        self.assertEqual(sr._framing({"blocking": "Kelly đứng giữa khung"}), "")
        self.assertIn("keep exactly the shape", sr.prompt([("a", 2.0), ("b", 2.0)], []))


class MarkTests(unittest.TestCase):
    def test_two_pictures_with_the_same_file_name_get_two_marked_copies(self):
        """#8 2026-09-28: KENTA's and MAXIM's sheets are both 7.png — one marked copy served both, MAXIM's clip showed KENTA."""
        from PIL import Image
        from core import seedance_refs as sr
        root = tempfile.mkdtemp()
        paths = []
        for folder, colour in (("24", (200, 0, 0)), ("33", (0, 0, 200))):
            os.makedirs(os.path.join(root, folder))
            p = os.path.join(root, folder, "7.png")
            Image.new("RGB", (64, 64), colour).save(p)
            paths.append(p)
        out = os.path.join(root, "marked")
        a, b = sr.mark(paths[0], out), sr.mark(paths[1], out)
        self.assertNotEqual(a, b)
        self.assertNotEqual(Image.open(a).getpixel((32, 50)), Image.open(b).getpixel((32, 50)))


class PromptLessonsTests(unittest.TestCase):
    """S4.8 / S4.9 (2026-09-29): lessons of the Volcengine Seedance 2.5 提示词指南 and the ClipAI model guide
    (research/craft/trung_quoc/PROMPT.md)."""

    def test_time_marks_only_for_a_model_that_reads_them(self):
        from core import seedance_refs as sr
        parts = [("a", 1.4), ("b", 2.2), ("c", 3.1)]
        for model in ("seedance", "seedance-2.0", "seedance-fast", "dreamina-seedance-2-0-fast-260128", None):
            text = sr.prompt(parts, [], model=model)
            self.assertIn("Shot 2: b.", text)
            self.assertNotIn(" s):", text)                                   # 2.0 / Fast answer shot numbers, not seconds
        text = sr.prompt(parts, [], model="dreamina-seedance-2-5-260628")
        for want in ("Shot 1 (0–1 s)", "Shot 2 (1–4 s)", "Shot 3 (4–7 s)"):   # whole seconds, back to back
            self.assertIn(want, text)
        self.assertEqual(sr.whole_marks([0.4, 0.4, 3]), [(0, 1), (1, 2), (2, 4)])   # every shot keeps a second

    def test_identity_pictures_follow_the_order_characters_first_appear(self):
        from core import seedance_refs as sr
        text = sr.prompt([("a", 2), ("b", 2)], [("KENTA", "k.png"), ("KELLY", "l.png")])
        self.assertLess(text.index("Image 3 is KENTA"), text.index("Image 4 is KELLY"))

    def test_strong_emotion_is_softened_and_the_eyes_guarded(self):
        from core import seedance_refs as sr
        d = {"size": "CU", "performance": {"intensity": 5, "face": "extremely furious snarl", "eyes": "wide, ecstatic"}, "action": "x"}
        t = sr.shot_motion(d)
        self.assertIn("angry snarl", t)
        self.assertNotIn("extremely", t)
        self.assertIn("no glowing eyes", t)
        calm = {"size": "MS", "performance": {"intensity": 2, "face": "a small smile"}, "action": "x"}
        self.assertNotIn("glowing", sr.shot_motion(calm))                  # guard only where strong emotion invites the fault

    def test_a_shot_with_three_body_actions_is_flagged_not_blocked(self):
        from core import seedance_refs as sr
        rows = [{"data": {"action": "Kelly turns, walks to the door then falls"}}, {"data": {"action": "Kenta looks up"}}]
        self.assertEqual(sr.busy_shots(rows), [1])

    def test_reference_pictures_are_not_sharper_than_the_output(self):
        import tempfile
        from PIL import Image
        from core import seedance_refs as sr
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "big.png")
            Image.new("RGB", (2400, 1600), (90, 90, 90)).save(src)
            out = sr.mark(src, os.path.join(d, "m"))
            self.assertLessEqual(max(Image.open(out).size), sr.REF_MAX_SIDE)


if __name__ == "__main__":
    unittest.main()
