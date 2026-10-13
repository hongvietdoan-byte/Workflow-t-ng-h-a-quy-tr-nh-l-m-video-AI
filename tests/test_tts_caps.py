"""Lỗi 9 (#27 tổng kết 13/10, cờ tts_lowercase_caps): TTS đọc sai thanh chữ IN HOA tiếng Việt ("BÌNH TĨNH" → "bình tỉnh"). Trước khi
gửi TTS: hạ chữ thường từ tiếng Việt viết hoa, giữ tên/từ game; phụ đề (dialogue trong CSDL) giữ chữ gốc. Cờ tắt: chữ gửi như cũ."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import audio_lib, tts_caps, voice
from core.db import connect
from core.pipeline import Pipeline


class LowerCapsTests(unittest.TestCase):
    def test_vietnamese_capitals_are_lowered(self):
        self.assertEqual(tts_caps.lower_caps("Kelly ơi, BÌNH TĨNH!"), "Kelly ơi, bình tĩnh!")
        self.assertEqual(tts_caps.lower_caps("NHANH LÊN, CHẠY ĐI"), "nhanh lên, chạy đi")      # a no-mark word inside a marked run

    def test_game_words_and_names_stay(self):
        self.assertEqual(tts_caps.lower_caps("BOOYAH! QUÉT SẠCH ĐỘI"), "BOOYAH! quét sạch đội")
        self.assertEqual(tts_caps.lower_caps("cầm SKORP BẮN ĐI", keep=["SKORP"]), "cầm SKORP bắn đi")
        self.assertEqual(tts_caps.lower_caps("HAWK, RPK, M7 và OK"), "HAWK, RPK, M7 và OK")
        self.assertEqual(tts_caps.lower_caps("MINH ƠI", keep=["Minh"]), "MINH ơi")                # a kept name, not guessed
        self.assertEqual(tts_caps.lower_caps("NHANH"), "NHANH")                                    # alone, no mark: not guessed

    def test_a_name_with_vietnamese_marks_is_lowered_like_any_word(self):
        self.assertEqual(tts_caps.lower_caps("XÚC TU ĐỎ tới", keep=["XÚC TU ĐỎ"]), "xúc tu đỏ tới")

    def test_speakable_follows_the_flag(self):
        with mock.patch.dict(os.environ, {"FEATURE_TTS_LOWERCASE_CAPS": "0"}):
            self.assertEqual(voice.speakable("BÌNH TĨNH", {}), "BÌNH TĨNH")                        # flag off: as before
        with mock.patch.dict(os.environ, {"FEATURE_TTS_LOWERCASE_CAPS": "1"}):
            self.assertEqual(voice.speakable("BÌNH TĨNH, OB55", {"OB55": "ô bê năm mươi lăm"}), "bình tĩnh, ô bê năm mươi lăm")


class Audio:
    name = "mock"

    def __init__(self):
        self.sent = []

    def generate_tts(self, text, voice_actor_id, model="eleven_v3", language_code=None, name="tts", params=None):
        self.sent.append(text)
        return f"a{len(self.sent)}"


class GenerateTests(unittest.TestCase):
    """The real send path: voice.generate → audio_lib.submit_tts → provider.generate_tts (mock, 0 USD)."""

    def setUp(self):
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("caps")
        self.sid = self.p.create_scene(self.pid, 1, "s")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(
            {"shot_no": 1, "dialogue": [{"speaker": "LỜI DẪN", "text": "BÌNH TĨNH, BOOYAH cùng SKORP"}]}, ensure_ascii=False), self.sid))
        self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'LỜI DẪN', 'x')", (self.pid,))
        self.p.conn.execute("INSERT INTO assets(id, game, kind, name) VALUES (433, 'FF', 'prop', 'SKORP')")
        self.p.conn.commit()
        voice.set_profile(self.p.conn, self.pid, "LỜI DẪN", {"voice_id": 30169, "voice_name": "clone 2"})
        self.data = tempfile.mkdtemp()

    def test_flag_on_sends_lower_case_and_keeps_the_original_for_subtitles(self):
        audio = Audio()
        with mock.patch.dict(os.environ, {"FEATURE_TTS_LOWERCASE_CAPS": "1"}):
            voice.generate(self.p.conn, self.pid, audio, self.data, ledger=False)
        self.assertEqual(audio.sent, ["bình tĩnh, BOOYAH cùng SKORP"])
        e = [x for x in audio_lib.load(audio_lib.assets_dir(self.data, self.pid)) if x.get("scene_id")][0]
        self.assertEqual(e["text"], "BÌNH TĨNH, BOOYAH cùng SKORP")                                # subtitles: the line as written
        self.assertTrue(e.get("caps_lowered"))

    def test_flag_off_sends_as_before(self):
        audio = Audio()
        with mock.patch.dict(os.environ, {"FEATURE_TTS_LOWERCASE_CAPS": "0"}):
            voice.generate(self.p.conn, self.pid, audio, self.data, ledger=False)
        self.assertEqual(audio.sent, ["BÌNH TĨNH, BOOYAH cùng SKORP"])
        e = [x for x in audio_lib.load(audio_lib.assets_dir(self.data, self.pid)) if x.get("scene_id")][0]
        self.assertNotIn("caps_lowered", e)


if __name__ == "__main__":
    unittest.main()
