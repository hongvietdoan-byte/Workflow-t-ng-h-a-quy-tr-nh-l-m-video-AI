"""Short-video script format (kịch bản "ANH CHỌN AI?", 2026-09-24): sections named by their time on screen, separator rows, and the
speaker on its own line with the quoted line under it. Before the fix the opening section was dropped as a preamble, TWIST / ENDING
were merged into the previous scene and no dialogue line was found."""
import unittest

from core import dialogue, prompts, script_parser

SCRIPT = """KỊCH BẢN FREE FIRE: “ANH CHỌN AI?”
THỜI LƯỢNG: 55–58 GIÂY
CẤU TRÚC:
CINEMATIC MỞ ĐẦU → GAMEPLAY → TWIST → CINEMATIC KẾT
-----------------------------------
CINEMATIC MỞ ĐẦU – 0–8 GIÂY
-----------------------------------
CẬN CẢNH:
Kelly đứng một mình trong bóng tối.
Kelly:
“Anh thật sự… chọn anh ấy sao?”
Kenta im lặng.
-----------------------------------
CẢNH 1 – 8–20 GIÂY
-----------------------------------
Maxim:
“Kenta! Ông với Kelly cãi nhau à?”
-----------------------------------
TWIST – 44–50 GIÂY
-----------------------------------
HỆ THỐNG:
“Maxim đã bị hạ.”
FLASHBACK NGẮN:
Kenta:
“Nếu tôi phải hy sinh… hãy dùng nó cứu Maxim.”
TEXT CUỐI:
“Có những lời nói dối…
chỉ để bảo vệ người mình yêu.”""".splitlines()


class ScriptFormatTests(unittest.TestCase):
    def test_timed_sections_are_scenes_and_the_opening_is_kept(self):
        scenes = script_parser.split_scenes(SCRIPT)
        self.assertEqual([s.heading for s in scenes], ["CINEMATIC MỞ ĐẦU – 0–8 GIÂY", "CẢNH 1 – 8–20 GIÂY", "TWIST – 44–50 GIÂY"])
        self.assertNotIn("-----", scenes[0].text)
        self.assertFalse(script_parser.is_heading("THỜI LƯỢNG: 55–58 GIÂY"))
        self.assertFalse(script_parser.is_heading("CINEMATIC MỞ ĐẦU → GAMEPLAY → TWIST → CINEMATIC KẾT"))

    def test_a_speaker_on_its_own_line_is_joined_to_the_quote_and_screen_text_is_not_a_voice(self):
        scenes = script_parser.split_scenes(SCRIPT)
        self.assertEqual(dialogue.lines(scenes[0].text), [("KELLY", "Anh thật sự… chọn anh ấy sao?")])
        self.assertEqual(dialogue.lines(scenes[2].text), [("KENTA", "Nếu tôi phải hy sinh… hãy dùng nó cứu Maxim.")])
        self.assertEqual(scenes[2].characters, ["KENTA"])                     # HỆ THỐNG is on-screen text, not a speaker
        self.assertEqual(scenes[0].characters, ["KELLY"])                     # "CẬN CẢNH:" is a camera note, not a speaker

    def test_the_end_card_is_still_found(self):
        card, rest = script_parser.split_end_card(script_parser.split_scenes(SCRIPT))
        self.assertEqual(card, "Có những lời nói dối… chỉ để bảo vệ người mình yêu.")
        self.assertNotIn("TEXT CUỐI", rest[-1].text)

    def test_the_preamble_stops_at_the_first_timed_section(self):
        head = prompts.script_preamble({"script_text": "\n".join(SCRIPT)})
        self.assertIn("THỜI LƯỢNG: 55–58 GIÂY", head)
        self.assertNotIn("Kelly đứng một mình", head)
        self.assertNotIn("-----", head)


class DirectorFrameTests(unittest.TestCase):
    def test_the_target_length_is_read_from_the_script(self):
        self.assertEqual(prompts.target_seconds("THỜI LƯỢNG: 55–58 GIÂY"), (55, 58))
        self.assertEqual(prompts.target_seconds("Duration: 60s"), (60, 60))
        self.assertIsNone(prompts.target_seconds("CẢNH 1 – 8–20 GIÂY"))

    def test_the_director_gets_the_total_and_each_timed_section(self):
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("t")
        p.set_project_field(pid, "shot_mode", "per_shot")
        script_parser.import_scenes(p, pid, script_parser.split_scenes(SCRIPT), full_text="\n".join(SCRIPT))
        block = prompts.duration_block(p, pid)
        self.assertIn("55–58 giây", block)
        self.assertIn("tổng các shot ≈ 8 giây", block)                      # CINEMATIC MỞ ĐẦU – 0–8 GIÂY
        self.assertRegex(block, r"thoại \d+ câu cần ~[\d.]+ giây nói")      # 3rd run: 11 spoken shots shorter than their line
        self.assertIn("Shot có thoại: `duration_s` ≥", block)
        self.assertIn("# Thời lượng bắt buộc", prompts.build_director_bundle(p, pid))

    def test_system_text_becomes_on_screen_text_never_a_voice(self):
        from core import shots
        shot = {"size": "WS", "role": "action", "duration_s": 2, "image_prompt": "x", "action": "Maxim bị hạ",
                "dialogue": [{"speaker": "HỆ THỐNG", "text": "Maxim đã bị hạ."}, {"speaker": "KENTA", "text": "Maxim!"}]}
        data = shots.shot_data({"idx": 5}, shot, 1)
        self.assertEqual(data["dialogue"], [{"speaker": "KENTA", "text": "Maxim!"}])
        self.assertEqual(data["on_screen_text"], ["Maxim đã bị hạ."])
        self.assertNotIn("HỆ THỐNG", data["text"])


class LineFidelityTests(unittest.TestCase):
    def setUp(self):
        from core.db import connect
        from core.pipeline import Pipeline
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("t")
        self.p.set_project_field(self.pid, "shot_mode", "per_shot")
        script_parser.import_scenes(self.p, self.pid, script_parser.split_scenes(SCRIPT), full_text="\n".join(SCRIPT))

    def answer(self, lines):
        return {"scenes": [{"idx": 1, "shots": [{"dialogue": [{"speaker": w, "text": t} for w, t in lines]}]}]}

    def test_an_invented_or_reworded_line_is_sent_back(self):
        from core import llm_io
        with self.assertRaises(llm_io.SchemaError):
            llm_io._check_lines(self.p, self.pid, self.answer([("KELLY", "Anh thật sự chọn cô ấy sao?"),
                                                              ("MAXIM", "Kenta! Ông với Kelly cãi nhau à?"),
                                                              ("KENTA", "Nếu tôi phải hy sinh… hãy dùng nó cứu Maxim.")]))

    def test_dropping_a_line_needs_the_person_s_permission(self):
        from core import llm_io
        kept = self.answer([("KELLY", "“Anh thật sự… chọn anh ấy sao?”"), ("MAXIM", "Kenta! Ông với Kelly cãi nhau à?")])
        with self.assertRaises(llm_io.SchemaError) as e:
            llm_io._check_lines(self.p, self.pid, kept)
        self.assertIn("thiếu câu thoại", str(e.exception))
        self.p.set_project_field(self.pid, "dialogue_trim", 1)
        llm_io._check_lines(self.p, self.pid, kept)                           # allowed now (quotes/case do not matter)
        self.assertIn("Được phép bỏ bớt câu thoại", prompts.duration_block(self.p, self.pid))

    def test_a_dropped_line_that_the_next_line_answers_is_flagged(self):
        """Run 4 of "ANH CHỌN AI?" dropped "Kelly, nghe anh giải thích…" and kept "Không cần." — the reply then answers nothing."""
        from core import shots
        script = ["CẢNH 3 – 34–44 GIÂY", "Kelly:", "“Anh nói sẽ không để mất em…”", "Kenta:", "“Kelly, nghe anh giải thích…”",
                  "Kelly:", "“Không cần.”", "Maxim:", "“Ông làm cô ấy khóc rồi.”"]
        pid = self.p.create_project("cuts")
        self.p.set_project_field(pid, "shot_mode", "per_shot")
        script_parser.import_scenes(self.p, pid, script_parser.split_scenes(script), full_text="\n".join(script))
        shot = lambda who, said: {"size": "MS", "role": "dialogue", "duration_s": 2, "image_prompt": "x", "action": "x",  # noqa: E731
                                  "dialogue": [{"speaker": who, "text": said}]}
        shots.store_plan(self.p, pid, [{"idx": 1, "shots": [shot("KELLY", "Anh nói sẽ không để mất em…"), shot("KELLY", "Không cần.")]}])
        cuts = {c["text"]: c for c in shots.dialogue_cuts(self.p, pid)}
        self.assertEqual(set(cuts), {"Kelly, nghe anh giải thích…", "Ông làm cô ấy khóc rồi."})
        self.assertTrue(cuts["Kelly, nghe anh giải thích…"]["answered"])      # "Không cần." answers it
        self.assertFalse(cuts["Ông làm cô ấy khóc rồi."]["answered"])         # last line of the scene

    def test_silent_micro_shots_and_unreadable_wides_are_warned(self):
        from core import shots
        warn = shots.pacing_warnings([{"size": "WS", "role": "setup", "duration_s": 0.5},
                                      {"size": "MS", "role": "insert", "duration_s": 0.6},
                                      {"size": "WS", "role": "setup", "duration_s": 1.2},
                                      {"size": "MS", "role": "reaction", "duration_s": 1.0}])
        self.assertTrue(any("shot 1: 0.5s không thoại" in w for w in warn))
        self.assertFalse(any(w.startswith("shot 2:") for w in warn))           # a quick insert may be that short
        self.assertTrue(any("shot 3: toàn cảnh 1.2s" in w for w in warn))
        self.assertFalse(any(w.startswith("shot 4:") for w in warn))


if __name__ == "__main__":
    unittest.main()
