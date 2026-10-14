"""C5b / Đ12v3 mục 2 (cờ `mix_bus`, TẮT): nhạc nén riêng dưới bus hiệu ứng (SFX) 8–12 dB, nối tiếp sau bus giọng. Cờ tắt → lệnh trộn và
khóa âm thanh y như trước."""
import os
import subprocess
import tempfile
import unittest
from unittest import mock

import pytest

from core import audio_lib, delivery, ffmpeg_studio, music_cues


def _ffmpeg():
    try:
        return ffmpeg_studio.find_ffmpeg()
    except ffmpeg_studio.FFmpegNotFound:
        pytest.skip("ffmpeg not installed")


EXTRAS = [{"path": "v.wav", "start": 1.0, "volume": 1.0, "kind": "tts"},
          {"path": "s.wav", "start": 2.0, "volume": 0.8, "kind": "sound_effect"},
          {"path": "amb.wav", "start": 0.0, "volume": 0.3, "key": False}]


class CommandTests(unittest.TestCase):
    def _graph(self, extras):
        cmd = ffmpeg_studio.build_extras_mix_cmd("in.mkv", extras, "out.mp4", has_audio=True, duck=True)
        return cmd[cmd.index("-filter_complex") + 1]

    def test_without_bus_marks_the_command_is_the_old_one(self):
        old = ("[1:a]adelay=1000|1000,volume=1.0[e0];[2:a]adelay=2000|2000,volume=0.8[e1];[3:a]adelay=0|0,volume=0.3[e2];"
               "[e0][e1]amix=inputs=2:normalize=0:duration=longest,asplit=2[vk][vm];"
               f"[vk]apad[vkp];[0:a][vkp]{ffmpeg_studio.DUCK_EVEN}[bed];"
               f"[bed][vm][e2]amix=inputs=3:normalize=0:duration=longest,{ffmpeg_studio.PEAK_LIMIT},apad[a]")
        self.assertEqual(self._graph(EXTRAS), old)                            # a "kind" field changes nothing

    def test_effects_bus_presses_the_music_after_the_voices(self):
        g = self._graph([dict(e, bus="sfx") if e.get("kind") == "sound_effect" else e for e in EXTRAS])
        self.assertIn(f"[0:a][vkp]{ffmpeg_studio.DUCK_EVEN}[bv]", g)
        self.assertIn(f"[bv][skp]{ffmpeg_studio.DUCK_SFX}[bed]", g)
        self.assertIn("[bed][vm][sm][e2]amix=inputs=4", g)                    # every sound still plays at its own level
        only = self._graph([{"path": "s.wav", "start": 2.0, "volume": 0.8, "bus": "sfx"}])
        self.assertIn(f"[0:a][skp]{ffmpeg_studio.DUCK_SFX}[bed]", only)
        self.assertNotIn(ffmpeg_studio.DUCK_EVEN, only)
        self.assertIn("[bed][sm]amix=inputs=2", only)


class DepthTests(unittest.TestCase):
    def test_music_dips_8_to_12_db_under_effects_the_voice_curve_does_not(self):
        _ffmpeg()
        for level in (-28, -20, -14):
            got = music_cues.sfx_duck_depth(level)
            self.assertTrue(8.0 <= got <= 12.0, (level, got))
        self.assertLess(music_cues.sfx_duck_depth(-26, ffmpeg_studio.DUCK_EVEN), 8.0)    # why effects get their own bus


class RealMixTests(unittest.TestCase):
    def test_the_built_command_runs_and_the_music_dips_under_a_hit(self):
        ff = _ffmpeg()
        with tempfile.TemporaryDirectory() as d:
            video, sfx, out = (os.path.join(d, n) for n in ("in.mkv", "s.wav", "out.mp4"))
            subprocess.run([ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=8:r=24", "-f", "lavfi", "-i",
                            "sine=f=220:d=8:r=44100", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-c:a", "pcm_s16le", video], check=True)
            subprocess.run([ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=c=white:a=0.5:d=3:r=44100", "-ac", "2", sfx],
                           check=True)
            ffmpeg_studio.run(ffmpeg_studio.build_extras_mix_cmd(video, [{"path": sfx, "start": 3.0, "volume": 1.0, "bus": "sfx"}], out,
                                                                 has_audio=True, ffmpeg=ff, duck=True))
            self.assertTrue(os.path.exists(out))
            self.assertAlmostEqual(ffmpeg_studio.probe_duration(out), 8.0, delta=0.2)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.pid = 5
        directory = audio_lib.assets_dir(self.d, self.pid)
        os.makedirs(directory, exist_ok=True)
        self.dir = directory

    def _with_effect(self):
        path = os.path.join(self.dir, "hit.wav")
        with open(path, "wb") as f:
            f.write(b"RIFF")
        return [{"path": path, "start": 1.0, "volume": 1.0, "kind": "sound_effect"}]

    def test_audio_key_unchanged_when_off_and_changes_when_on(self):
        extras = self._with_effect()
        with mock.patch.object(audio_lib, "mix_list", return_value=extras), mock.patch.object(delivery, "selected_music", return_value=None), \
                mock.patch.object(delivery, "second_music", return_value=None), mock.patch.object(delivery, "_arc_cues", return_value=None):
            with mock.patch("core.features.on", return_value=False):
                off = delivery.audio_hash(self.d, self.pid)
            with mock.patch("core.features.on", side_effect=lambda n: n == "mix_bus"):
                on = delivery.audio_hash(self.d, self.pid)
            with mock.patch("core.features.on", side_effect=lambda n: n == "mix_bus"), \
                    mock.patch.object(audio_lib, "mix_list", return_value=[dict(extras[0], kind="tts")]):
                voices_only_on = delivery.audio_hash(self.d, self.pid)
            with mock.patch("core.features.on", return_value=False), \
                    mock.patch.object(audio_lib, "mix_list", return_value=[dict(extras[0], kind="tts")]):
                voices_only_off = delivery.audio_hash(self.d, self.pid)
        self.assertNotEqual(off, on)
        self.assertEqual(voices_only_on, voices_only_off)                   # no effect: the flag changes nothing


class RenderTests(unittest.TestCase):
    def test_render_marks_effects_on_their_bus_only_with_the_flag(self):
        from core import final_cut
        from core.db import connect
        from core.pipeline import Pipeline
        ff = _ffmpeg()
        d = tempfile.mkdtemp()
        p = Pipeline(connect(":memory:"))
        pid = p.create_project("mix bus")
        p.create_scene(pid, 1, "s1")
        clip = final_cut.clip_path(d, pid, 1)
        os.makedirs(os.path.dirname(clip), exist_ok=True)
        subprocess.run([ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=d=2:s=128x72:r=24", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", clip], check=True)
        p.conn.commit()
        mixed = [{"path": "v.wav", "start": 0.5, "volume": 1.0, "kind": "tts"}, {"path": "s.wav", "start": 1.0, "volume": 1.0,
                                                                              "kind": "sound_effect"}]
        got = {}

        def fake_render(paths, out, durations, transition, fade, track, volume, extras, *a, **k):
            got["extras"] = [dict(e) for e in extras]
            with open(out, "wb") as f:
                f.write(b"x")

        for flags in (set(), {"mix_bus"}):
            with mock.patch("core.features.on", side_effect=lambda n: n in flags), mock.patch.object(audio_lib, "mix_list", return_value=mixed), \
                    mock.patch.object(audio_lib, "missing_in_mix", return_value=[]), mock.patch.object(ffmpeg_studio, "render_final", side_effect=fake_render), \
                    mock.patch("core.formats.spec", return_value={"render": None}), mock.patch.object(delivery, "_loudness", return_value={}), \
                    mock.patch.object(ffmpeg_studio, "probe_duration", return_value=2.0):
                try:
                    delivery.render(p, pid, d, music_path=None, settings=delivery.get_settings(p, pid))
                except Exception:  # noqa: BLE001 - only what reached the mix matters here
                    pass
            self.assertIn("extras", got, flags)
            buses = [e.get("bus") for e in got.pop("extras")]
            self.assertEqual(buses, [None, "sfx"] if "mix_bus" in flags else [None, None], flags)


if __name__ == "__main__":
    unittest.main()
