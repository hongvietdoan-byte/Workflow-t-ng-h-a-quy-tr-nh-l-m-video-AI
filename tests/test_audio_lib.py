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
                mock.patch.object(os, "remove", side_effect=removed.append):
            f.render_final(["a", "b"], "o.mp4", [5, 5], music="m.mp3", extras=[{"path": "x.mp3", "start": 1, "volume": 1}])
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[1][-1], "o.mp4.music.mp4")
        self.assertEqual(calls[2][-1], "o.mp4")
        self.assertIn("amix=inputs=2", " ".join(calls[2]))
        self.assertEqual([r for r in removed if r.startswith("o.mp4")], ["o.mp4.silent.mp4", "o.mp4.music.mp4"])

    def test_render_final_extras_without_music(self):
        calls = []
        with mock.patch.object(f, "find_ffmpeg", return_value="ffmpeg"), mock.patch.object(f, "run", side_effect=calls.append), \
                mock.patch.object(os, "remove"):
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
