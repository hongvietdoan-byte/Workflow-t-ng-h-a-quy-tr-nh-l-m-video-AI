"""Kế hoạch V4 GĐ3 — lip sync for the whole video: which shots, the shot's own voice at the timeline's seconds, Seedance
reference_audio at generation, post lip sync (sync.so adapter), the voice kept at the synced seconds, the no-lip-sync flag lifted."""
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from core import audio_lib, lipsync, storyboard_gate, voice
from core.adapters.clipai import ClipAIVideoProvider
from core.adapters.syncso import SyncLipSync
from core.providers import ProviderError
from tests.test_adapters import TOKEN, FakeTransport, ctx_of, ok
from tests.test_sound_lib import NEEDS_FFMPEG

ON = {"FEATURE_LIP_SYNC": "1"}


def shot(size="CU", speaker="KELLY", cast=("KELLY",), **extra):
    return {"size": size, "characters": list(cast), "dialogue": [{"speaker": speaker, "text": "Em hiểu rồi."}], "shot_no": 1, **extra}


class MethodTests(unittest.TestCase):
    def test_which_shots_get_their_mouth_matched_and_how(self):
        self.assertEqual(lipsync.method_for(shot()), "post")
        self.assertEqual(lipsync.method_for(shot(lip_sync=True)), "generate")                     # a marked close-up
        self.assertEqual(lipsync.method_for(shot("MS", lip_sync=True)), "post")                   # marked but not close: post
        self.assertEqual(lipsync.method_for(shot(speaker="KENTA")), "skip")                       # the speaker is off screen
        self.assertEqual(lipsync.method_for(shot("EWS")), "skip")
        self.assertEqual(lipsync.method_for(shot(start_frame="Kelly with her back to camera")), "skip")
        self.assertEqual(lipsync.method_for({"size": "CU", "characters": ["KELLY"]}), "skip")     # nobody speaks
        self.assertEqual(lipsync.method_for(shot(lip_sync=False)), "skip")

    def test_the_no_lip_sync_flag_is_lifted_only_when_the_feature_is_on(self):
        s = shot()
        self.assertTrue(storyboard_gate.lip_sync_risk(s))
        with mock.patch.dict(os.environ, ON):
            self.assertFalse(storyboard_gate.lip_sync_risk(s))

    def test_line_offsets_follow_the_timeline_rule(self):
        self.assertEqual(lipsync.line_offsets([{"duration_ms": 1000}, {"duration_ms": 500}]),
                         [voice.LEAD, round(voice.LEAD + 1.0 + voice.GAP, 3)])


@NEEDS_FFMPEG
class ShotAudioTests(unittest.TestCase):
    def test_the_shot_audio_has_the_clip_length_and_the_lines_at_their_seconds(self):
        from core.ffmpeg_studio import find_ffmpeg
        ff = find_ffmpeg()
        data = tempfile.mkdtemp()
        adir = audio_lib.assets_dir(data, 1)
        os.makedirs(adir, exist_ok=True)
        for n in (1, 2):
            subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.8",
                            os.path.join(adir, f"l{n}.wav")], check=True)
        audio_lib._save(adir, [{"kind": "tts", "scene_id": 7, "line": n, "state": "succeeded", "file": f"l{n}.wav", "duration_ms": 800}
                               for n in (1, 2)])
        seg = lipsync.shot_audio(data, 1, 7, 4.0, ff)
        self.assertEqual(seg["offsets"], [0.3, 1.25])
        probe = subprocess.run([ff, "-i", seg["path"]], capture_output=True, text=True, errors="replace").stderr
        self.assertIn("Duration: 00:00:04.0", probe)
        self.assertIsNone(lipsync.shot_audio(data, 1, 99, 4.0, ff))                              # no voiced line: None


class SeedanceAudioTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.t.on("POST", "/api/kling/seedance-video-submit", ok({"tasks": [{"task_id": "S", "task_status": "submitted"}]}))
        d = tempfile.mkdtemp()
        self.image, self.audio = os.path.join(d, "a.png"), os.path.join(d, "v.wav")
        with open(self.image, "wb") as f:
            f.write(b"\x89PNG-fake")
        with open(self.audio, "wb") as f:
            f.write(b"RIFF-fake")
        self.p = ClipAIVideoProvider(TOKEN, "https://clipai.example", self.t)

    def test_the_voice_goes_as_reference_audio(self):
        self.p.submit(self.image, "Kelly speaks", None, 5, model="seedance", reference_audio=[self.audio])
        ctx = ctx_of(self.t.calls[0])
        self.assertIn({"type": "audio_url", "audio_url": {"url": ""}, "role": "reference_audio"}, ctx["content"])
        self.assertIn(b'name="audio_files"', self.t.calls[0]["body"])

    def test_limits_and_kling_refusal(self):
        with self.assertRaises(ProviderError):
            self.p.submit(self.image, "x", None, 5, model="kling", reference_audio=[self.audio])
        with self.assertRaises(ProviderError) as ctx:
            self.p.submit(self.image, "x", None, 5, model="seedance", reference_audio=[self.audio] * 4)   # 2.0: at most 3
        self.assertEqual(ctx.exception.code, "rule_violation")


class RunnerTests(unittest.TestCase):
    @mock.patch.dict(os.environ, ON)
    def test_a_marked_close_up_goes_to_seedance_with_its_voice(self):
        from core import batch, llm_io, llm_runner, model_router
        from core.providers import MockVideoProvider
        from core.runner import VideoRunner
        from tests.test_v3 import _approve_all_images, _approve_all_motion, kenta_project
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        rows = p.conn.execute("SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
        target = next(r for r in rows if json.loads(r["data"]).get("dialogue"))
        data = json.loads(target["data"])
        speaker = data["dialogue"][0]["speaker"]
        data.update(size="CU", lip_sync=True, characters=sorted(set((data.get("characters") or []) + [speaker])))
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), target["id"]))
        p.conn.commit()
        dd = tempfile.mkdtemp()
        _approve_all_images(p, pid, dd)
        _approve_all_motion(p, pid, dd)
        self.assertEqual(model_router.scene_choice(p.conn, target["id"])["model"], "seedance")
        fake = os.path.join(dd, "seg.wav")
        open(fake, "wb").close()
        prov = MockVideoProvider()
        vr = VideoRunner(p, prov, dd)
        vr.max_concurrent = 99
        with mock.patch("core.lipsync.shot_audio", return_value={"path": fake, "offsets": [0.3], "lines": [1], "seconds": 4}):
            batch.queue_videos(p, pid, dd)
            for _ in range(10):
                vr.submit_pending(pid)
                vr.poll_once(pid)
        job = p.conn.execute("SELECT external_id FROM jobs WHERE scene_id=? AND type='video_gen' AND external_id IS NOT NULL",
                             (target["id"],)).fetchone()
        self.assertEqual(prov._tasks[job["external_id"]]["reference_audio"], [fake])
        self.assertEqual(lipsync.index(dd, pid)[str(target["id"])]["state"], "done")
        self.assertIn(target["id"], lipsync.synced_scene_ids(dd, pid))

    def test_off_by_default_nothing_changes(self):
        self.assertFalse(lipsync.enabled())


class DirectorFieldTests(unittest.TestCase):
    def test_v4_fields_of_the_director_survive_into_the_shot(self):
        from core import shots
        scene = {"idx": 1, "characters": ["KELLY"], "weather": "rain"}
        s = {"size": "CU", "angle": "eye", "role": "main", "action": "Kelly speaks", "image_prompt": "p", "duration_s": 3,
             "lip_sync": True, "plate_spot": "plaza_front", "lines": []}
        data = shots.shot_data(scene, s, 1)
        self.assertEqual((data["lip_sync"], data["weather"], data["plate_spot"]), (True, "rain", "plaza_front"))

    @mock.patch.dict(os.environ, ON)
    def test_the_director_is_told_when_lip_sync_is_on(self):
        from core import prompts
        from tests.test_v3 import kenta_project
        p, pid = kenta_project()
        self.assertIn("Khớp môi đang BẬT", prompts.duration_block(p, pid) if hasattr(prompts, "duration_block") else
                      prompts.build_director_bundle(p, pid))


class SyncAdapterTests(unittest.TestCase):
    def test_submit_poll_download(self):
        t = FakeTransport()
        t.on("POST", "/v2/generate", lambda call: _json({"id": "g1", "status": "PENDING"}))
        states = iter([{"id": "g1", "status": "PROCESSING"}, {"id": "g1", "status": "COMPLETED", "outputUrl": "https://cdn.sync/x.mp4"}])
        t.on("GET", "/v2/generate/g1", lambda call: _json(next(states)))
        t.on("GET", "/x.mp4", lambda call: _raw(b"MP4"))
        d = tempfile.mkdtemp()
        v, a = os.path.join(d, "c.mp4"), os.path.join(d, "a.wav")
        for f in (v, a):
            open(f, "wb").write(b"x")
        s = SyncLipSync("key-1", "https://api.sync.example", t)
        self.assertEqual(s.submit(v, a), "g1")
        self.assertEqual(t.calls[0]["headers"]["x-api-key"], "key-1")
        self.assertNotIn("Authorization", t.calls[0]["headers"])
        self.assertEqual(s.status("g1").state, "running")
        self.assertEqual(s.status("g1").state, "succeeded")
        out = s.download("g1", os.path.join(d, "o.mp4"))
        self.assertEqual(open(out, "rb").read(), b"MP4")

    def test_without_a_key_it_says_so(self):
        from core.adapters import syncso
        with mock.patch.dict(os.environ, {"SYNC_API_KEY": ""}):
            self.assertIsNone(syncso.from_env_or_none())


def _json(obj):
    from core.adapters.http import HttpResponse
    return HttpResponse(200, json.dumps(obj).encode())


def _raw(body):
    from core.adapters.http import HttpResponse
    return HttpResponse(200, body)


if __name__ == "__main__":
    unittest.main()
