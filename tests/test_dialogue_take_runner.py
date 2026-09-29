"""S4.2 (feature dialogue_take — option (c) of the S4.6 A/B, chosen by the user 2026-09-29): shots where a speaker's face is seen go in their
Seedance 2.5 reference group clip with ONE voice track of the group's lines at their seconds + the lines, speakers and seconds in the
prompt; after the cut each shot's lines are laid where its mouth moves (shift = real start − planned start)."""
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from core import audio_lib, ffmpeg_studio, lipsync, llm_runner, model_router, seedance_refs, shots, voice
from tests.test_seedance_refs import real_png
from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project

ENV = {"FEATURE_SEEDANCE_REF_GROUPS": "1", "FEATURE_LIP_SYNC": "1", "FEATURE_DIALOGUE_TAKE": "1"}


def wav(path, seconds=0.8):
    subprocess.run([ffmpeg_studio.find_ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t",
                    str(seconds), path], check=True)


class DialogueTakeRunnerTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p, self.pid = kenta_project(shot_mode="per_shot")
        self.data = tempfile.mkdtemp()
        llm_runner.run_director(self.p, self.pid, llm_runner.MockLlm())
        rows = shots.shots_of(self.p, self.pid)
        first = rows[0]["data"]["story_scene"]
        whole = [r for r in rows if r["data"]["story_scene"] == first]
        scene = whole[:2]
        for r in whole[2:]:                                      # the rest of the scene: another continuity group
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(dict(r["data"], sequence=2), ensure_ascii=False), r["id"]))
        self.assertEqual(len(scene), 2, "the mock plan needs 2+ shots in its first scene")
        names = ["KELLY", "MAXIM"]
        for r, who, line in zip(scene, names, ("Của anh à?", "Không ai lấy được!")):
            d = dict(r["data"], sequence=1, duration_s=2.0, size="MS", characters=names,
                     dialogue=[{"speaker": who, "text": line}])
            for k in ("plate_mode", "lip_sync", "video_route"):
                d.pop(k, None)
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), r["id"]))
        self.p.conn.commit()
        self.ids = [r["id"] for r in scene]
        adir = audio_lib.assets_dir(self.data, self.pid)
        items = []
        for sid, who, n, line in zip(self.ids, names, (1, 2), ("Của anh à?", "Không ai lấy được!")):
            wav(os.path.join(adir, f"l{n}.wav"))
            items.append({"kind": "tts", "scene_id": sid, "line": 1, "speaker": who, "text": line, "state": "succeeded",
                          "file": f"l{n}.wav", "duration_ms": 800, "dialogue": True})
        audio_lib._save(adir, items)

    def _ready(self):
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        _approve_all_images(self.p, self.pid, self.data)
        _approve_all_motion(self.p, self.pid, self.data)
        for sid in self.ids:
            real_png(shots.approved_image_path(self.p.conn, self.data, self.pid, sid))
        return VideoRunner(self.p, MockVideoProvider(polls_to_finish=1), self.data)

    def test_a_speaking_medium_shot_is_a_take_and_stays_in_its_group(self):
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.ids[0],)).fetchone()["data"])
        self.assertEqual(lipsync.method_for(d), "take")                  # MS: was "skip" (no sync.so) — no lip sync at all
        with mock.patch.dict(os.environ, {"FEATURE_DIALOGUE_TAKE": "0"}):
            self.assertEqual(lipsync.method_for(d), "skip")
        self.assertEqual([r["id"] for r in shots.group_of(self.p.conn, self.ids[0])], self.ids)
        choice = model_router.scene_choice(self.p.conn, self.ids[0])
        self.assertEqual(choice["model"], "seedance-2.5")
        self.assertIn("S4.2", choice["reason"])

    def test_the_group_clip_carries_one_track_and_the_lines_at_their_seconds(self):
        vr = self._ready()
        leader = self.p.job(self.p.create_job(self.ids[0], "video_gen"))
        self.p.create_job(self.ids[1], "video_gen")
        args = vr._submit_args(leader)
        self.assertEqual(args[4], "seedance-2.5")
        self.assertIn("DIALOGUE TIMELINE", args[1])
        self.assertIn('"Của anh à?"', args[1])
        self.assertIn('"Không ai lấy được!"', args[1])
        self.assertIn("[00:00 - 00:02] Dialogue (KELLY", args[1])
        segs = vr._take_segments(leader, shots.group_of(self.p.conn, self.ids[0]))
        self.assertEqual([s["scene_id"] for s in segs], self.ids)
        self.assertAlmostEqual(segs[0]["start"], voice.LEAD)
        self.assertGreater(segs[1]["start"], segs[0]["end"])            # the second shot's line after its shot start
        problems = vr._ref_lint(leader)
        self.assertFalse(problems and "tiếng Việt" in problems, problems)   # the spoken lines stay Vietnamese on purpose
        kw = vr._submit_kwargs(leader)
        self.assertEqual(len(kw["reference_audio"]), 1)
        self.assertTrue(os.path.exists(kw["reference_audio"][0]))
        idx = lipsync.index(self.data, self.pid)
        self.assertEqual({idx[str(s)]["method"] for s in self.ids}, {"take"})
        self.assertEqual(idx[str(self.ids[1])]["planned_start"], segs[1]["shot_start"])

    def test_after_the_cut_each_shot_is_synced_with_its_shift(self):
        vr = self._ready()
        leader = self.p.job(self.p.create_job(self.ids[0], "video_gen"))
        group = shots.group_of(self.p.conn, self.ids[0])
        vr._take_audio(leader, group)
        planned = lipsync.index(self.data, self.pid)[str(self.ids[1])]["planned_start"]
        vr._take_done(leader, group, [0.0, planned + 0.4])               # the model cut 0.4 s later than planned
        idx = lipsync.index(self.data, self.pid)
        self.assertEqual(idx[str(self.ids[1])]["state"], "done")
        self.assertAlmostEqual(idx[str(self.ids[1])]["shift"], 0.4)
        self.assertEqual(set(self.ids) & lipsync.synced_scene_ids(self.data, self.pid), set(self.ids))
        clips = [{"scene_id": sid, "path": "x", "requested_sec": 2.0} for sid in self.ids]
        with mock.patch("core.final_cut.collect_clips_for_render", return_value=clips):
            voice.place_on_timeline(self.p.conn, self.pid, self.data, durations=[2.0, 2.0])
        items = {e["scene_id"]: e for e in audio_lib.load(audio_lib.assets_dir(self.data, self.pid))}
        self.assertAlmostEqual(items[self.ids[0]]["start"], voice.LEAD)
        self.assertAlmostEqual(items[self.ids[1]]["start"], round(2.0 + voice.LEAD - 0.4, 2))   # moved back onto the mouth

    def test_without_voiced_lines_nothing_is_attached(self):
        audio_lib._save(audio_lib.assets_dir(self.data, self.pid), [])
        vr = self._ready()
        leader = self.p.job(self.p.create_job(self.ids[0], "video_gen"))
        self.assertEqual(vr._take_segments(leader, shots.group_of(self.p.conn, self.ids[0])), [])
        self.assertNotIn("reference_audio", vr._submit_kwargs(leader))
        self.assertNotIn("DIALOGUE TIMELINE", vr._submit_args(leader)[1])

    def test_the_prompt_limit_follows_the_model(self):
        long = "x" * 4500
        self.assertTrue(seedance_refs.lint_group(long, 1, 1, 1, [4], False, model="seedance-fast"))
        self.assertFalse(seedance_refs.lint_group(long, 1, 1, 1, [4], False, model="seedance-2.5"))
