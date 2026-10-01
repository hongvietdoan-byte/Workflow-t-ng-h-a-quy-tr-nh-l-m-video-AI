"""Kế hoạch V4, GĐ1 — M16 (video fingerprint knows model + sound), M18 (price comparison keeps overrides / multi-shot),
M19 (multi-shot is not measured by the prompt it does not send; each shot carries the "Avoid")."""
import os
import tempfile
import unittest

from core import batch, lineage, llm_io, llm_runner, model_router
from core.adapters.clipai import KLING_SHOT_PROMPT_LIMIT, ClipAIVideoProvider
from core.providers import MockVideoProvider
from core.runner import VideoRunner
from tests.test_adapters import TOKEN, FakeTransport, ctx_of, ok
from tests.test_v2 import Base


class VideoFingerprintTests(Base):
    def _clip(self):
        self.approve_images()
        llm_runner.run_motion(self.p, self.pid, llm_runner.MockLlm(), self.data)
        sid = self.sid(1)
        llm_io.approve_motion_prompt(self.p, sid)
        vr = VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data)
        batch.queue_videos(self.p, self.pid, self.data)
        vr.submit_pending(self.pid)
        vr.poll_once(self.pid)
        return sid

    def test_changing_the_model_of_a_shot_makes_its_clip_outdated(self):
        sid = self._clip()
        self.assertIsNone(lineage.scan(self.p.conn, self.pid)[sid]["video_stale"])
        current = model_router.scene_choice(self.p.conn, sid)["model"]
        model_router.set_override(self.p.conn, sid, "seedance" if current != "seedance" else "kling")
        self.assertIn("model", lineage.scan(self.p.conn, self.pid)[sid]["video_stale"])

    def test_turning_on_generated_sound_makes_the_clip_outdated(self):
        sid = self._clip()
        self.p.conn.execute("UPDATE projects SET video_audio=1 WHERE id=?", (self.pid,))
        self.p.conn.commit()
        self.assertTrue(lineage.scan(self.p.conn, self.pid)[sid]["video_stale"])

    def test_a_clip_stamped_before_m16_is_not_a_false_alarm(self):
        sid = self._clip()
        mp = self.p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()
        aspect = self.p.project(self.pid)["aspect"]
        from core import formats
        self.p.conn.execute("UPDATE jobs SET input_hash=? WHERE scene_id=? AND type='video_gen'",
                            (lineage.video_input_hash(mp, formats.project_aspect(self.p.project(self.pid))), sid))
        self.p.conn.commit()
        self.assertIsNone(lineage.scan(self.p.conn, self.pid)[sid]["video_stale"])
        self.assertTrue(aspect)


class CompareTotalsTests(Base):
    def test_other_priorities_keep_the_shot_the_person_chose(self):
        self.approve_images()
        llm_runner.run_motion(self.p, self.pid, llm_runner.MockLlm(), self.data)
        sid = self.sid(1)
        model_router.set_override(self.p.conn, sid, "seedance-2.5")
        for priority in model_router.PRIORITIES:
            row = next(r for r in model_router.plan(self.p.conn, self.pid, priority=priority) if r["scene_id"] == sid)
            self.assertEqual(row["model"], "seedance-2.5", priority)


class MultiShotPromptTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.t.on("POST", "/api/kling/omni-video-submit", ok({"tasks": [{"task_id": "T", "task_status": "submitted"}]}))
        self.image = os.path.join(tempfile.mkdtemp(), "img.png")
        with open(self.image, "wb") as f:
            f.write(b"\x89PNG-fake")
        self.p = ClipAIVideoProvider(TOKEN, "https://clipai.example", self.t)

    def test_a_long_leader_prompt_does_not_block_a_multi_shot_request(self):
        shots = [{"prompt": "shot one", "duration": 3}, {"prompt": "shot two", "duration": 3}]
        self.p.submit(self.image, "x" * 3000, None, 6, multi_prompt=shots)          # the leader text is never sent
        ctx = ctx_of(self.t.calls[0])
        self.assertEqual([s["prompt"] for s in ctx["multi_prompt"]], ["shot one", "shot two"])
        self.assertNotIn("prompt", ctx)

    def test_each_shot_carries_the_avoid_when_it_fits(self):
        self.p.negative = "append"
        shots = [{"prompt": "short shot", "duration": 3}, {"prompt": "y" * (KLING_SHOT_PROMPT_LIMIT - 5), "duration": 3}]
        self.p.submit(self.image, "lead", "extra fingers", 6, multi_prompt=shots)
        prompts = [s["prompt"] for s in ctx_of(self.t.calls[0])["multi_prompt"]]
        self.assertEqual(prompts[0], "short shot Avoid: extra fingers")
        self.assertNotIn("Avoid", prompts[1])                                      # no room: the shot's own words win
        self.assertLessEqual(max(len(p) for p in prompts), KLING_SHOT_PROMPT_LIMIT)


class VideoRuleTests(unittest.TestCase):
    """W10: rules from data/provider_rules.json `video_models`, checked before anything is sent."""
    def test_rules_catch_what_clipai_would_refuse_or_silently_change(self):
        from core import video_rules
        self.assertEqual(video_rules.problems("kling-v3-omni", 5), [])
        self.assertTrue(video_rules.problems("kling-v3-omni", 12, reference_video=True))        # 3–10 s with a reference video
        self.assertTrue(video_rules.problems("dreamina-seedance-2-0-fast-260128", 5, resolution="1080p"))
        self.assertEqual(video_rules.problems("dreamina-seedance-2-0-260128", 5, resolution="1080p"), [])
        self.assertTrue(video_rules.problems("dreamina-seedance-2-5-260628", 5, resolution="1080p"))
        self.assertTrue(video_rules.problems("kling-video-o1", 7, last_frame=True))              # O1 first+last: 5 or 10 s
        self.assertTrue(video_rules.problems("dreamina-seedance-2-0-260128", 5, audios=4))        # ≤ 3 audios on 2.0
        self.assertEqual(video_rules.problems("dreamina-seedance-2-5-260628", 5, audios=4), [])
        self.assertEqual(video_rules.problems("unknown-model", 99), [])
        self.assertTrue(any("Seedance 2.0 Fast" in line for line in video_rules.summary_lines()))

    def test_the_adapter_refuses_before_sending(self):
        from core.providers import ProviderError
        t = FakeTransport()
        image = os.path.join(tempfile.mkdtemp(), "img.png")
        with open(image, "wb") as f:
            f.write(b"\x89PNG-fake")
        provider = ClipAIVideoProvider(TOKEN, "https://clipai.example", t)
        with self.assertRaises(ProviderError) as ctx:
            provider.submit(image, "run", None, 5, model="seedance-fast", resolution="1080p")
        self.assertEqual(ctx.exception.code, "rule_violation")
        self.assertFalse(ctx.exception.transient)
        self.assertEqual(t.calls, [])                                                            # nothing was sent, nothing billed


class PilotCoverageTests(unittest.TestCase):
    """W2: the pilot shots cover every character, every place and close / medium / wide framing before repeating anything."""
    def test_pilot_covers_people_places_and_framing(self):
        import json
        from core import pilot
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("w2")
        shots = [(["KELLY"], "town", "MS"), (["KELLY"], "town", "MS"), (["KELLY"], "town", "CU"), (["KENTA"], "tower", "WS"),
                 (["KELLY", "MAXIM"], "town", "MS"), (["KELLY"], "tower", "MS")]
        for i, (cast, place, size) in enumerate(shots, 1):
            sid = p.create_scene(pid, i, f"s{i}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                           (json.dumps({"characters": cast, "location": place, "size": size}), sid))
        p.conn.commit()
        ids = {r["idx"]: r["id"] for r in p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=?", (pid,))}
        chosen = pilot.pick(p, pid, size=3)
        by_idx = {v: k for k, v in ids.items()}
        picked = sorted(by_idx[c] for c in chosen)
        self.assertIn(4, picked)                                      # Kenta + the tower + a wide shot
        self.assertIn(5, picked)                                      # Maxim
        self.assertNotIn(2, picked)                                   # a copy of shot 1 tests nothing new


class LookTrustTests(unittest.TestCase):
    """W8: the QC agent earns the right to skip the storyboard checkpoint per look pack: >= 50 pictures, >= 90% agreement,
    <= 2% lenient mistakes."""
    def _pictures(self, p, pid, n, disagree=0, lenient=0, both_reject=0):
        """n pictures: the first `lenient` passed by QC but rejected by the person, the next ones up to `disagree` failed by QC but
        approved by the person, the rest agreed (QC pass + person approve)."""
        idx = p.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (pid,)).fetchone()[0] + 1
        sid = p.create_scene(pid, idx, f"s{idx}")
        for i in range(n):
            jid = p.create_job(sid, "image_gen")
            ai_pass, person = (True, "reject") if i < lenient else (False, "approve") if i < disagree else (True, "approve")
            if i >= n - both_reject:
                ai_pass, person = False, "reject"                      # QC and the person both reject: a correct catch
            p.conn.execute("INSERT INTO qc_results (job_id, criterion, score, threshold_at_time) VALUES (?,?,?,?)",
                           (jid, "overall", 0.9 if ai_pass else 0.3, 0.7))
            p.conn.execute("INSERT INTO review_log (job_id, reviewer_type, decision, decided_at) VALUES (?,?,?,datetime('now'))",
                           (jid, "user", person))
        p.conn.commit()

    def test_trust_needs_enough_pictures_and_agreement(self):
        from core import effectiveness
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("w8")
        p.set_project_field(pid, "look", "FF_INGAME")
        self._pictures(p, pid, 40)
        self.assertFalse(effectiveness.look_trust(p.conn, "FF_INGAME", None)["trusted"])      # only 40 pictures
        self._pictures(p, pid, 20, disagree=3)
        t = effectiveness.look_trust(p.conn, "FF_INGAME", None)
        self.assertEqual(t["pairs"], 60)
        self.assertFalse(t["trusted"])                                                          # B2 01/10: nothing rejected → no proof yet
        self._pictures(p, pid, 6, both_reject=6)
        t = effectiveness.look_trust(p.conn, "FF_INGAME", None)
        self.assertEqual((t["pairs"], t["rejected"], t["lenient_rate"]), (66, 6, 0.0))
        self.assertTrue(t["trusted"])                                                           # 63/66 = 95%, 6 rejected, all caught
        self._pictures(p, pid, 10, lenient=3)
        self.assertFalse(effectiveness.look_trust(p.conn, "FF_INGAME", None)["trusted"])      # 3 of 9 rejected pictures it passed
        self.assertEqual(effectiveness.look_trust(p.conn, "ANIME", None)["pairs"], 0)          # another look starts from zero


    def test_b2_missing_every_rejected_picture_is_not_trusted(self):
        """01/10 B2: 50 pictures, the person rejected 1, QC passed all 50 → it missed 100% of the rejected ones (was 2% of all)."""
        from core import effectiveness
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("b2")
        p.set_project_field(pid, "look", "B2LOOK")
        self._pictures(p, pid, 50, lenient=1)
        t = effectiveness.look_trust(p.conn, "B2LOOK", None)
        self.assertEqual((t["pairs"], t["rejected"], t["lenient_rate"]), (50, 1, 1.0))
        self.assertFalse(t["trusted"])


class BibleGapTests(unittest.TestCase):
    """O6: the run stops at the Bible when a character in the shots has no Lock (and no approved standard profile)."""
    def test_a_character_without_a_lock_is_reported(self):
        import json
        from core import autopilot
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("o6")
        sid = p.create_scene(pid, 1, "s")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"characters": ["KELLY"]}), sid))
        p.conn.commit()
        llm_io.add_character(p, pid, "KELLY", "sprinter")
        llm_io.add_character(p, pid, "EXTRA", "not in any shot")
        gaps = autopilot.bible_gaps(p, pid)
        self.assertEqual(gaps["no_lock"], ["KELLY"])                 # EXTRA is in no shot: not asked for
        self.assertEqual(gaps["no_picture"], ["KELLY"])
        p.conn.execute("UPDATE characters SET lock_rules=? WHERE name='KELLY'", ("bob haircut, yellow track suit",))
        p.conn.commit()
        self.assertEqual(autopilot.bible_gaps(p, pid)["no_lock"], [])


class TimedMusicTests(unittest.TestCase):
    """The score timed on the real cut (core/music_timing.py, made for trial 2A) is now what the automatic run asks for in shot
    projects: two drafts, the one whose changes land on the section turns is kept."""
    def test_autopilot_asks_for_two_timed_drafts_and_keeps_one(self):
        from core import autopilot, music
        from core.music import MockAudioProvider
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        from tests.test_v3 import kenta_project
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        data = tempfile.mkdtemp()
        audio = MockAudioProvider()
        ctx = autopilot.Context(data, ImageRunner(p, MockImageProvider(), data), VideoRunner(p, MockVideoProvider(), data),
                                llm_runner.MockLlm(), audio, lambda *a, **k: None)
        self.assertEqual(autopilot._music_phase(p, pid, ctx), "Nhạc nền: đang tạo")
        drafts_dir, selected_dir = music.project_dirs(data, pid)
        drafts = music.load_drafts(drafts_dir)
        self.assertEqual(len(drafts), autopilot.TIMED_DRAFTS)
        self.assertIn("BPM", drafts[0]["prompt"])
        for _ in range(5):
            if autopilot._music_phase(p, pid, ctx) is None:
                break
        self.assertTrue(os.listdir(selected_dir))


class RecoverToolRelinkTests(unittest.TestCase):
    """`tools/recover_clips.py --relink`: the find-by-prompt recovery of the automatic run, for jobs written off earlier."""
    def test_the_tool_reopens_a_written_off_job_on_its_real_task(self):
        import sys
        from unittest import mock
        from tests.test_not_created import RequeuedTaskTest
        case = RequeuedTaskTest("test_a_job_already_written_off_is_reopened_on_its_real_task")
        case.setUp()
        case.queue_then_create()
        if case.p.state(case.job).value == "queued":
            case.p.start(case.job)
        case.p.fail(case.job, "not_found: không thấy task")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
        import recover_clips
        with mock.patch("core.db.connect", return_value=case.p.conn):
            res = recover_clips.relink("ignored.sqlite", case.runner.provider, case.dir, [case.pid])
        self.assertEqual(len(res["rows"]), 1)
        new = res["rows"][0]["new_job"]
        self.assertEqual(case.p.job(new)["external_id"], "omni:REAL1")
        self.assertIn("nối lại", res["text"])
        self.assertEqual(case.fake.created, 1)                                  # nothing sent again


class RefusedThenSwitchedTests(unittest.TestCase):
    """M14: Seedance refused the shot, the shot was moved to Kling — and then nothing sent it again (a refusal is not a transient
    error). Now the new try is queued at once and goes out on Kling."""
    def test_the_switched_shot_is_sent_again_on_kling(self):
        from core import batch, model_router
        from core.providers import MockVideoProvider, ProviderError
        from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        data = tempfile.mkdtemp()
        _approve_all_images(p, pid, data)
        _approve_all_motion(p, pid, data)
        provider = MockVideoProvider()
        real_submit, calls = provider.submit, []

        def refuse_first(*a, **k):
            calls.append(a)
            if len(calls) == 1:
                raise ProviderError("[InputImageSensitiveContentDetected.PrivacyInformation] The request failed because the input "
                                    "image 'content[1]' may contain real person.", code="bad_request")
            return real_submit(*a, **k)
        provider.submit = refuse_first
        vr = VideoRunner(p, provider, data)
        vr.max_concurrent = 1
        batch.queue_videos(p, pid, data)
        first = p.conn.execute("SELECT id, scene_id FROM jobs WHERE project_id=? AND type='video_gen' ORDER BY id LIMIT 1",
                               (pid,)).fetchone()
        vr.submit_pending(pid)
        again = p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen' AND parent_job_id=?",
                               (first["scene_id"], first["id"])).fetchone()
        self.assertIsNotNone(again)
        self.assertEqual(again["state"], "queued")
        self.assertEqual(again["retry_count"], 1)
        self.assertEqual(model_router.scene_choice(p.conn, first["scene_id"])["model"], "kling")


if __name__ == "__main__":
    unittest.main()
