import json
import os
import tempfile
import unittest
from unittest import mock

from core import audio_lib, cost, ffmpeg_studio as f
from core.db import connect
from core.llm_io import lock_character_bible, store_scene_analysis, unlock_character_bible, update_character
from core.music import MockAudioProvider
from core.pipeline import Pipeline
from core.providers import ProviderError
from core.subtitles import Cue
from tests.test_llm_io_preflight import ANALYSIS


class AudioLibTests(unittest.TestCase):
    def setUp(self):
        self.dir = audio_lib.assets_dir(tempfile.mkdtemp(), 1)
        self.provider = MockAudioProvider()

    def test_sfx_and_tts_flow_and_mix_list(self):
        audio_lib.submit_sfx(self.provider, self.dir, "door slam", 2)
        audio_lib.submit_tts(self.provider, self.dir, "Xin chào", 1, "Mock voice")
        self.assertEqual(audio_lib.refresh(self.provider, self.dir)["succeeded"], 2)
        self.assertEqual(audio_lib.mix_list(self.dir), [])  # nothing switched on yet
        audio_lib.set_mix(self.dir, 0, True, 3.5, 0.8)
        audio_lib.set_mix(self.dir, 1, True, 0, 1.0)
        mix = audio_lib.mix_list(self.dir)
        self.assertEqual([(m["start"], m["volume"]) for m in mix], [(3.5, 0.8), (0.0, 1.0)])
        self.assertTrue(all(os.path.exists(m["path"]) for m in mix))
        self.assertIn("Mock voice", audio_lib.load(self.dir)[1]["label"])

    def test_an_effect_over_a_spoken_line_is_halved_in_the_mix(self):
        """Trial #8 (2026-09-28): gunshot + impact + beep summed over a voice line, then limited = "tiếng rè"."""
        for i, (kind, start, ms) in enumerate((("tts", 1.0, 2000), ("sound_effect", 2.5, 500), ("sound_effect", 4.0, 500))):
            path = os.path.join(self.dir, f"x{i}.wav")
            open(path, "wb").close()
            audio_lib.add_local(self.dir, path, f"e{i}", start, 1.0, ms, {"kind": kind} if kind == "tts" else None)
        vols = [m["volume"] for m in audio_lib.mix_list(self.dir)]
        self.assertEqual(vols, [1.0, audio_lib.SFX_UNDER_SPEECH, 1.0])       # 2,5 s is inside the line (1–3 s); 4 s is after it

    def test_a_switched_on_sound_whose_file_is_gone_is_named(self):
        """S14.4 C1b (04/10): mix_list dropped it silently — the video came out without that sound and nobody knew."""
        path = os.path.join(self.dir, "boom.wav")
        open(path, "wb").close()
        audio_lib.add_local(self.dir, path, "Tiếng nổ", 1.0, 1.0, 500, None)
        self.assertEqual(audio_lib.missing_in_mix(self.dir), [])
        os.remove(os.path.join(self.dir, audio_lib.load(self.dir)[0]["file"]))
        self.assertEqual(audio_lib.mix_list(self.dir), [])
        self.assertEqual(audio_lib.missing_in_mix(self.dir), ["Tiếng nổ"])

    def test_cannot_use_unfinished_asset_and_remove_deletes_file(self):
        audio_lib.submit_sfx(self.provider, self.dir, "wind")
        with self.assertRaises(ValueError):
            audio_lib.set_mix(self.dir, 0, True, 0, 1)
        audio_lib.refresh(self.provider, self.dir)
        path = os.path.join(self.dir, audio_lib.load(self.dir)[0]["file"])
        audio_lib.remove(self.dir, 0)
        self.assertFalse(os.path.exists(path))
        self.assertEqual(audio_lib.load(self.dir), [])

    def test_submit_error_is_recorded_not_retried(self):
        class Rejecting(MockAudioProvider):
            def generate_sfx(self, *a, **k):
                raise ProviderError("too long", code="prompt_too_long")

        entry = audio_lib.submit_sfx(Rejecting(), self.dir, "x")
        self.assertEqual((entry["state"], entry["message"]), ("failed", "too long"))
        self.assertEqual(audio_lib.refresh(self.provider, self.dir)["failed"], 1)

    def _tts_with_duration(self, text: str, voice: str, ms: int) -> int:
        """Submit + finish a voice-over line, then force its real duration (the mock always answers 1500ms —
        these tests need to control it to exercise the overlap math)."""
        audio_lib.submit_tts(self.provider, self.dir, text, 1, voice)
        audio_lib.refresh(self.provider, self.dir)
        items = audio_lib.load(self.dir)
        index = len(items) - 1
        items[index]["duration_ms"] = ms
        audio_lib._save(self.dir, items)
        return index

    def test_overlapping_tts_detects_crosstalk_and_clears_once_fixed(self):
        a = self._tts_with_duration("A", "V", 3000)
        b = self._tts_with_duration("B", "V", 3000)
        audio_lib.set_mix(self.dir, a, True, 0.0, 1.0)
        audio_lib.set_mix(self.dir, b, True, 2.0, 1.0)     # starts before line a (ends at 3.0) finishes
        self.assertEqual(audio_lib.overlapping_tts(self.dir), [{"a": a, "b": b, "overlap": 1.0}])
        audio_lib.set_mix(self.dir, b, True, 3.5, 1.0)
        self.assertEqual(audio_lib.overlapping_tts(self.dir), [])

    def test_schedule_by_cues_pushes_the_next_line_past_the_real_end(self):
        """The planned cue timing (from an estimate made before the voice existed) has line B starting at 2.0s,
        but line A's REAL audio (4.0s) runs past that — schedule_by_cues must push B out instead of trusting
        the stale estimate."""
        self._tts_with_duration("Hello there", "V", 4000)
        self._tts_with_duration("General Kenobi", "V", 2000)
        cues = [Cue(0.0, 2.0, "Hello there", "A", 1), Cue(2.0, 4.0, "General Kenobi", "B", 1)]
        changed = audio_lib.schedule_by_cues(self.dir, cues, min_gap=0.1)
        self.assertEqual(changed, 2)
        items = audio_lib.load(self.dir)
        self.assertEqual((items[0]["use"], items[0]["start"]), (True, 0.0))
        self.assertEqual(items[1]["start"], 4.1)  # pushed past line A's real end (4.0) + the 0.1s gap
        self.assertEqual(audio_lib.overlapping_tts(self.dir), [])

    def test_schedule_by_cues_leaves_unmatched_lines_alone(self):
        self._tts_with_duration("Hi", "V", 1000)
        changed = audio_lib.schedule_by_cues(self.dir, [Cue(0.0, 1.0, "Bye", "A", 1)])
        self.assertEqual(changed, 0)
        self.assertFalse(audio_lib.load(self.dir)[0]["use"])

    def test_ledger_records_each_submission(self):
        p = Pipeline(connect())
        pid = p.create_project("t")

        class Real(MockAudioProvider):
            name = "clipai-audio"

        audio_lib.submit_sfx(Real(), self.dir, "a", ledger=(p.conn, pid))
        audio_lib.submit_tts(Real(), self.dir, "b", 3, model="eleven_v3", ledger=(p.conn, pid))
        rows = p.conn.execute("SELECT model FROM usage_events ORDER BY id").fetchall()
        self.assertEqual([r["model"] for r in rows], ["eleven_text_to_sound_v2", "eleven_v3"])
        self.assertEqual(cost.spend_summary(p.conn, pid, cost.load_pricing())["audios"], 2)


class MixCommandTests(unittest.TestCase):
    def test_extras_are_delayed_scaled_and_mixed_with_existing_audio(self):
        cmd = f.build_extras_mix_cmd("v.mp4", [{"path": "a.mp3", "start": 1.5, "volume": 0.5},
                                              {"path": "b.mp3", "start": 0, "volume": 1}], "o.mp4", has_audio=True)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("adelay=1500|1500", graph)
        self.assertIn("volume=0.5", graph)
        self.assertIn("[0:a][e0][e1]amix=inputs=3:normalize=0", graph)
        self.assertIn("apad", graph)
        self.assertIn("-shortest", cmd)
        no_music = f.build_extras_mix_cmd("v.mp4", [{"path": "a.mp3", "start": 0, "volume": 1}], "o.mp4", False)
        self.assertIn("[e0]amix=inputs=1", no_music[no_music.index("-filter_complex") + 1])
        with self.assertRaises(ValueError):
            f.build_extras_mix_cmd("v.mp4", [], "o.mp4", True)

    def test_render_final_chains_music_then_extras_and_cleans_temp_files(self):
        calls, removed = [], []
        with mock.patch.object(f, "find_ffmpeg", return_value="ffmpeg"), mock.patch.object(f, "run", side_effect=calls.append), \
                mock.patch.object(os, "remove", side_effect=removed.append), mock.patch.object(f, "_commit"):
            f.render_final(["a", "b"], "o.mp4", [5, 5], music="m.mp3", extras=[{"path": "x.mp3", "start": 1, "volume": 1}])
        self.assertEqual(len(calls), 3)
        staged = calls[2][-1]                     # D6: the last step writes a temp file next to o.mp4, moved onto it when done
        self.assertRegex(staged, r"^o\.part-[0-9a-f]{8}\.mp4$")
        self.assertEqual(calls[1][-1], staged + ".music.mkv")
        self.assertIn("pcm_s16le", calls[1])                  # A18: PCM between the two mixing steps, AAC once at the end
        self.assertIn("aac", calls[2])
        self.assertIn("amix=inputs=2", " ".join(calls[2]))
        self.assertEqual([r for r in removed if r.startswith("o.")], [staged + ".silent.mp4", staged + ".music.mkv"])

    def test_a_music_track_shorter_than_the_film_plays_again_crossfaded(self):
        """Trial #8 (2026-09-28): 68 s of music under 83 s of film — the last 15 s had no music."""
        self.assertEqual(f.music_loops(67.8, 83.0), 1)
        self.assertEqual(f.music_loops(20.0, 83.0), 4)          # 20 + 4 × 18,5 = 94 ≥ 83
        self.assertEqual(f.music_loops(90.0, 83.0), 0)
        self.assertEqual(f.music_loops(None, 83.0), 0)
        cmd = f.build_mux_music_cmd("v.mp4", "m.mp3", "o.mp4", 83.0, music_len=67.8)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("[1:a]asplit=2[mc0][mc1];[mc0][mc1]acrossfade=d=1.5[ml1];[ml1]atrim=0:83.0", graph)
        plain = f.build_mux_music_cmd("v.mp4", "m.mp3", "o.mp4", 60.0, music_len=67.8)
        self.assertTrue(plain[plain.index("-filter_complex") + 1].startswith("[1:a]atrim=0:60.0"))

    def test_render_final_extras_without_music(self):
        calls = []
        with mock.patch.object(f, "find_ffmpeg", return_value="ffmpeg"), mock.patch.object(f, "run", side_effect=calls.append), \
                mock.patch.object(os, "remove"), mock.patch.object(f, "_commit"):
            f.render_final(["a", "b"], "o.mp4", [5, 5], extras=[{"path": "x.mp3", "start": 0, "volume": 1}])
        self.assertEqual(len(calls), 2)
        self.assertIn("[e0]amix=inputs=1", " ".join(calls[1]))


class CharacterEditTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.p.create_scene(self.pid, 1, "CẢNH 1")
        store_scene_analysis(self.p, self.pid, ANALYSIS)

    def test_edit_updates_fields(self):
        update_character(self.p, self.pid, "Lyra", "Nữ, tóc đỏ", "áo choàng")
        row = self.p.conn.execute("SELECT description, wardrobe FROM characters WHERE name='Lyra'").fetchone()
        self.assertEqual((row["description"], row["wardrobe"]), ("Nữ, tóc đỏ", "áo choàng"))

    def test_rename_updates_scene_cast_and_rejects_duplicates(self):
        update_character(self.p, self.pid, "Lyra", "Nữ, tóc bạc", None, new_name="Lyra II")
        data = json.loads(self.p.conn.execute("SELECT data FROM scenes").fetchone()["data"])
        self.assertEqual(data["characters"], ["Lyra II"])
        with self.assertRaises(ValueError):
            update_character(self.p, self.pid, "Lyra II", "x", None, new_name="Nữ chiến binh Amazon")

    def test_locked_character_needs_unlock_and_validation(self):
        lock_character_bible(self.p, self.pid)
        with self.assertRaises(ValueError):
            update_character(self.p, self.pid, "Lyra", "khác")
        self.assertEqual(unlock_character_bible(self.p, self.pid), 2)
        with self.assertRaises(ValueError):
            update_character(self.p, self.pid, "Lyra", "   ")
        with self.assertRaises(KeyError):
            update_character(self.p, self.pid, "Nobody", "x")
        update_character(self.p, self.pid, "Lyra", "khác")


if __name__ == "__main__":
    unittest.main()
