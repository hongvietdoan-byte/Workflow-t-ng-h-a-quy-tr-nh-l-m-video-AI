"""S0.15 (người dùng 2026-09-29 "làm nốt hoàn thiện" M1–M8, research/craft/draft/nhac_luot2_doi_chieu.md): the music brief reads THIS
film — tone, motif, ending, tempo ceiling, how a turn arrives, sparse beds — instead of #8's love drama for every film."""
import json
import unittest
from unittest import mock

from core import claude_tasks, final_qc, music_fit, music_intent, music_timing, sound_intent
from core.db import connect
from core.llm_runner import LlmReply
from core.pipeline import Pipeline


def project(shots, genre=None, director=None, aspect="9:16", game="FF"):
    """shots: [(story_scene, mood, seconds, extra)]."""
    p = Pipeline(connect())
    pid = p.create_project("m", genre=genre, aspect=aspect, game=game)
    for i, (sc, mood, secs, extra) in enumerate(shots, 1):
        sid = p.create_scene(pid, i, f"s{i}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                       (json.dumps({"story_scene": sc, "mood": mood, "duration_s": secs, **extra}, ensure_ascii=False), sid))
    if director is not None:
        p.conn.execute("UPDATE projects SET director_raw=? WHERE id=?", (json.dumps(director), pid))
    p.conn.commit()
    return p, pid


DRAMA = [(1, "đau, kìm nén, sắp vỡ", 6.0, {}),
         (2, "bí mật, nghẹt thở", 6.0, {"sound": {"music": "cut"}}),
         (3, "hoảng loạn, khẩn cấp", 3.0, {"action": "Flashback: lời hứa"}),
         (3, "hoảng loạn, khẩn cấp", 3.0, {"sound": {"music": "in"}}),
         (4, "vỡ òa, ấm áp sau đau thương", 6.0, {"emotional_intent": "tình yêu được hóa giải, Kelly ôm lấy Kenta"})]
COMEDY = [(1, "tense but comedic, urgent squad banter", 6.0, {"emotional_intent": "căng và buồn cười cùng lúc"}),
          (2, "showy, thrilling, playful", 6.0, {}),
          (3, "comedic twist, cheeky", 6.0, {"emotional_intent": "người xem bật cười vì cú twist"})]


class ToneTests(unittest.TestCase):                       # M1
    def test_a_love_drama_keeps_its_love_motif(self):
        p, pid = project(DRAMA)
        b = music_timing.brief(p, pid)
        self.assertEqual(b["intent"]["tone"]["tone"], "drama")
        self.assertIn("vertical Free Fire short drama", b["prompt"])
        self.assertIn("One simple, memorable love motif", b["prompt"])
        self.assertIn("full at the end", b["prompt"])

    def test_a_comedy_gets_no_love_motif_and_no_drama(self):
        p, pid = project(COMEDY)
        b = music_timing.brief(p, pid)
        self.assertEqual(b["intent"]["tone"]["tone"], "comedy")
        text = b["prompt"]
        for gone in ("love motif", "short drama", "hopeful", "breathe slower"):
            self.assertNotIn(gone, text)
        self.assertIn("short comedy", text)
        self.assertIn("Comic timing", text)
        self.assertIn("comic: light pizzicato", text)             # "tense but comedic, urgent" is a joke, not panic
        self.assertIn("playful lightness", text)                  # not #8's "uneasy lightness"
        self.assertIn("comic button", text)

    def test_unknown_tone_is_neutral_and_said(self):
        p, pid = project([(1, "", 5.0, {}), (2, "", 5.0, {})])
        b = music_timing.brief(p, pid)
        self.assertIsNone(b["intent"]["tone"]["tone"])
        self.assertIn("short film", b["prompt"])
        self.assertNotIn("love motif", b["prompt"])
        self.assertTrue(b["notes"] and "giọng điệu chưa rõ" in b["notes"][0])      # CHUAN luật 1: never silent

    def test_the_directors_music_block_wins(self):
        p, pid = project(COMEDY, director={"music": {"tone": "drama", "motif": "promise theme", "ending": "cliffhanger"}})
        b = music_timing.brief(p, pid)
        self.assertEqual(b["intent"]["tone"]["source"], "director")
        self.assertIn("promise theme", b["prompt"])
        self.assertIn("cliffhanger", b["prompt"])
        self.assertIn("unresolved final hit at", b["prompt"])
        self.assertEqual(music_fit.planned(b["prompt"])["end"], b["film_s"])   # music_fit still finds the end mark

    def test_a_music_video_says_the_brief_is_only_a_draft(self):
        p, pid = project(COMEDY, genre="MUSIC_VIDEO")
        b = music_timing.brief(p, pid)
        self.assertIn("music video", b["prompt"])
        self.assertTrue(any("MV" in n for n in b["notes"]))

    def test_no_game_no_free_fire_and_landscape_not_vertical(self):
        p, pid = project(DRAMA, aspect="16:9", game="OTHER")
        text = music_timing.brief(p, pid)["prompt"]
        self.assertNotIn("Free Fire", text)
        self.assertNotIn("vertical", text)


class EndingTests(unittest.TestCase):                     # M2
    def test_a_drama_that_ends_cold_is_left_open(self):
        shots = DRAMA[:-1] + [(4, "đau, trống rỗng", 6.0, {"emotional_intent": "Kelly mất Kenta"})]
        p, pid = project(shots)
        b = music_timing.brief(p, pid)
        self.assertEqual(b["intent"]["ending"]["kind"], "open")
        self.assertNotIn("warm and hopeful", b["prompt"])
        self.assertIn("unresolved", b["prompt"])

    def test_a_flashback_without_a_motif_is_only_another_colour(self):
        p, pid = project([(1, "", 4.0, {}), (2, "", 4.0, {"action": "flashback: căn phòng cũ"}), (3, "", 4.0, {})])
        text = music_timing.brief(p, pid)["prompt"]
        self.assertIn("flashback: a thinner, distant colour", text)
        self.assertNotIn("dreamy and warm", text)


class DraftScoreTests(unittest.TestCase):                 # M3
    RISE = [-30.0] * 8 + [-12.0] * 8          # 0.5 s steps, turn at 4.0 s
    FALL = [-12.0] * 8 + [-40.0] * 3 + [-12.0] * 5     # a drop into near-silence at the turn, the music back after

    def score(self, levels, dirs):
        with mock.patch.object(music_timing, "loudness", return_value=list(levels)):
            return music_timing.score_draft("x.mp3", [4.0], 8.0, dirs=dirs)["score"]

    def test_a_turn_into_silence_rewards_the_draft_that_drops(self):
        self.assertGreater(self.score(self.FALL, ["down"]), self.score(self.RISE, ["down"]))
        self.assertGreater(self.score(self.RISE, ["up"]), self.score(self.FALL, ["up"]))
        self.assertGreater(self.score(self.FALL, ["change"]), 0)
        self.assertGreater(self.score(self.RISE, ["change"]), 0)

    def test_without_directions_it_is_the_old_rise_score(self):
        self.assertEqual(self.score(self.RISE, None), self.score(self.RISE, ["up"]))

    def test_the_brief_asks_down_where_the_director_cut_the_music(self):
        p, pid = project(DRAMA)
        b = music_timing.brief(p, pid)
        self.assertEqual(b["turn_dirs"][0], "down")                      # scene 2 opens on sound.music = cut
        self.assertEqual(len(b["turn_dirs"]), len(b["turns"]))

    def test_pick_best_follows_the_directions(self):
        levels = {"rise.mp3": self.RISE, "fall.mp3": self.FALL}
        with mock.patch.object(music_timing, "loudness", side_effect=lambda path, step=0.5: list(levels[path])):
            self.assertEqual(music_timing.pick_best(["rise.mp3", "fall.mp3"], [4.0], 8.0, dirs=["down"]), 1)
            self.assertEqual(music_timing.pick_best(["rise.mp3", "fall.mp3"], [4.0], 8.0), 0)


class TempoTests(unittest.TestCase):                      # M4
    BAR_128 = 240 / 128                     # sections one bar long at 128 BPM: only 128 puts every turn on a bar line

    def shots(self, mood):
        return [(k, mood, self.BAR_128, {}) for k in range(1, 6)]

    def test_the_ceiling_follows_the_tone(self):
        p, pid = project(self.shots("comedic, cheeky"))
        self.assertEqual(music_timing.brief(p, pid)["bpm"], 128)
        p, pid = project(self.shots("đau, khóc"))
        self.assertLessEqual(music_timing.brief(p, pid)["bpm"], music_timing.DRAMA_BPM_MAX)
        self.assertEqual(music_intent.TONES["drama"]["bpm_max"], music_timing.DRAMA_BPM_MAX)


class FunctionAndEntryTests(unittest.TestCase):           # M5
    def test_function_and_sudden_entry_reach_the_prompt(self):
        shots = [(1, "bí mật", 5.0, {"sound": {"music_fn": "hide"}}),
                 (2, "hoảng loạn", 5.0, {"sound": {"enter": "sudden", "music_fn": "reveal"}})]
        p, pid = project(shots)
        b = music_timing.brief(p, pid)
        self.assertIn("0:00.0 hides what the character feels", b["prompt"])
        self.assertIn("0:05.0 the reveal", b["prompt"])
        self.assertIn("Except at 0:05.0: there the change comes at once", b["prompt"])
        self.assertEqual(music_fit.planned(b["prompt"])["turns"], b["turns"])
        self.assertLessEqual(len(b["prompt"]), music_timing.PROMPT_MAX)

    def test_sound_intent_keeps_the_new_fields_and_reports_bad_ones(self):
        s, problems = sound_intent.clean({"music": "cut", "music_fn": "Tension", "enter": "sudden", "bed": "sparse"})
        self.assertEqual(s, {"music": "cut", "music_fn": "tension", "enter": "sudden", "bed": "sparse"})
        s, problems = sound_intent.clean({"music_fn": "sad violin", "bed": "loud"})
        self.assertIsNone(s)
        self.assertEqual(len(problems), 2)


class SparseBedTests(unittest.TestCase):                  # M6
    def plan(self, bed):
        datas = [{"sound": {"music": "cut", **({"bed": bed} if bed else {})}}] + [{}] * 4 + [{"sound": {"music": "in"}}]
        return sound_intent.music_plan(datas, [4.0] * 6)

    def test_a_sparse_stretch_may_stay_silent_longer(self):
        sparse, cont = self.plan("sparse"), self.plan(None)
        self.assertEqual(sparse["off"], [(0.0, 20.0)])
        self.assertEqual(sparse["auto_in"], [])
        self.assertEqual(cont["auto_in"], [8.0])                          # the #8 rule where the bed is continuous
        self.assertEqual(final_qc.check_music({"sound_intent": json.loads(json.dumps(sparse))}), [])
        self.assertTrue(final_qc.check_music({"sound_intent": {"off": [[0.0, 20.0]]}}))

    def test_the_directors_plan_is_not_warned_for_a_sparse_silence(self):
        shots = [{"duration_s": 4.0, "sound": {"music": "cut", "bed": "sparse"}}] + [{"duration_s": 4.0}] * 3 \
            + [{"duration_s": 4.0, "sound": {"music": "in", "bed": "continuous"}}]
        self.assertFalse([w for w in sound_intent.warnings(shots) if "nhạc tắt" in w])
        shots[0]["sound"].pop("bed")
        self.assertTrue([w for w in sound_intent.warnings(shots) if "nhạc tắt liền" in w])

    def test_the_brief_says_the_stretch_is_sparse(self):
        p, pid = project([(1, "", 5.0, {}), (2, "", 5.0, {"sound": {"bed": "sparse"}})])
        self.assertIn("very sparse, mostly resting", music_timing.brief(p, pid)["prompt"])


class ClaudeBriefTests(unittest.TestCase):                # M7
    def test_cues_are_kept_bad_ones_dropped_and_the_tone_is_sent(self):
        seen = {}

        class Fake:
            def complete(self, prompt, images=()):
                seen["prompt"] = prompt
                return LlmReply(json.dumps({"prompt": "Light comic score.", "duration_sec": 18, "cues": [
                    {"id": "1M1", "start": 0, "end": 6, "function": "nhịp hài", "enter": "soft", "exit": "cut"},
                    {"id": "1M2", "start": 6, "end": 9, "needed": False, "why": "lặng trước punchline"},
                    {"id": "1M3", "start": 9, "end": 5}]}))

        p, pid = project(COMEDY)
        b = claude_tasks.music_brief(p, pid, Fake())
        self.assertIn("# Giọng điệu: hài", seen["prompt"])
        self.assertIn("có điều kiện", seen["prompt"])
        self.assertEqual([c["id"] for c in b["cues"]], ["1M1", "1M2"])
        self.assertFalse(b["cues"][1]["needed"])
        self.assertEqual(len(b["notes"]), 1)

    def test_no_cues_is_the_old_brief(self):
        self.assertEqual(claude_tasks.clean_cues(None), ([], []))


class SpottingTests(unittest.TestCase):                   # M8
    def test_the_sheet_names_the_cut_the_tone_and_every_cue(self):
        from core import delivery
        p, pid = project(DRAMA)
        sheet = music_timing.spotting(p, pid)
        self.assertIn("theo bảng shot (chưa có bản dựng)", sheet)
        self.assertIn("chính kịch", sheet)
        self.assertIn("| 1M4 |", sheet)
        self.assertIn("almost silent", sheet)
        ids = [r["id"] for r in p.conn.execute("SELECT id FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]
        delivery.record(p, pid, "final", "FINAL_VIDEO.mp4", None, {"timeline": [{"scene_id": i, "seconds": 5.0} for i in ids]})
        self.assertIn("bản dựng #", music_timing.spotting(p, pid))

    def test_written_next_to_the_drafts(self):
        import os
        import tempfile
        p, pid = project(COMEDY)
        with tempfile.TemporaryDirectory() as d:
            path = music_timing.write_spotting(p, pid, d)
            self.assertTrue(path and os.path.exists(path))
            self.assertIn("hài", open(path, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
