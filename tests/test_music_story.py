"""Music brief that follows the story (after #8, người dùng 2026-09-28: "nhạc làm rẻ hơn nhiều so với làm video nên được quyền sáng tạo nhạc
cho hợp với các diễn biến trong clip"): timed on the render, a mood per scene read from the Director's Vietnamese moods, the story beats."""
import json
import unittest

from core import music_fit, music_timing
from core.db import connect
from core.pipeline import Pipeline

SHOTS = [  # (story_scene, mood, seconds planned, extra)
    (1, "đau, kìm nén, sắp vỡ", 4.0, {}),
    (2, "căng thẳng ẩn dưới vẻ đùa cợt", 5.0, {"sound": {"music": "in"}}),
    (3, "bí mật, nghẹt thở", 3.0, {"sound": {"music": "cut"}, "dialogue": [{"speaker": "KENTA", "text": "Không được để cô ấy biết."}]}),
    (3, "bí mật, nghẹt thở", 3.0, {"sound": {"music": "cut"}}),
    (4, "hoảng loạn, khẩn cấp rồi vỡ lẽ", 2.0, {"on_screen_text": ["Maxim đã bị hạ"], "action": "Maxim trúng đạn ngã gục"}),
    (4, "hoảng loạn, khẩn cấp rồi vỡ lẽ", 3.0, {"action": "Flashback: Kenta nói với Maxim về lời hứa"}),
    # S0.15 M1: the love motif is asked only when the story is about love (#8's last scene says so) — no longer for every film
    (5, "vỡ òa, ấm áp sau đau thương", 2.0, {"performance": {"intensity": 5}, "emotional_intent": "tình yêu được hóa giải"}),
    (5, "vỡ òa, ấm áp sau đau thương", 2.0, {}),
]


def project():
    p = Pipeline(connect())
    pid = p.create_project("music")
    ids = []
    for i, (sc, mood, secs, extra) in enumerate(SHOTS, 1):
        sid = p.create_scene(pid, i, f"s{i}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": sc, "mood": mood, "duration_s": secs, **extra}), sid))
        ids.append(sid)
    p.conn.commit()
    return p, pid, ids


class StoryBriefTests(unittest.TestCase):
    def test_each_scene_gets_the_music_of_its_vietnamese_mood(self):
        p, pid, _ = project()
        styles = [music_timing._style(s) for s in music_timing.sections(p, pid)]
        self.assertEqual([x.split(":")[0] for x in styles],
                         ["fragile", "uneasy lightness", "hushed suspense", "urgent", "warm resolution"])   # #8: 4 of 6 were "tense, driving"

    def test_the_story_beats_are_written_in(self):
        p, pid, _ = project()
        b = music_timing.brief(p, pid)
        text = b["prompt"]
        self.assertIn("love motif", text)
        self.assertIn("0:09.0 almost silent under the key lines", text.replace("0:09.0-0:12.0", "0:09.0"))
        self.assertIn("shock: a sharp low hit", text)
        self.assertIn("flashback:", text)
        self.assertIn("resolution:", text)
        self.assertNotIn("comes back in softly", text)                   # "in" on a scene start is the scene turn itself
        self.assertLessEqual(b["bpm"], music_timing.DRAMA_BPM_MAX)
        self.assertLessEqual(len(text), music_timing.PROMPT_MAX)
        self.assertEqual(music_fit.planned(text)["turns"], b["turns"])      # the turn line survives for music_fit

    def test_after_a_render_the_score_follows_the_render(self):
        from core import delivery
        p, pid, ids = project()
        planned = music_timing.timed_brief(p, pid)
        self.assertEqual(planned["film_s"], 24.0)
        delivery.record(p, pid, "final", "x.mp4", None, {"timeline": [{"scene_id": sid, "seconds": 5.0} for sid in ids]})
        after = music_timing.timed_brief(p, pid)
        self.assertEqual(after["film_s"], 40.0)                          # #8: composed on 64 s, cut 84,5 s
        self.assertEqual(after["turns"], [5.0, 10.0, 20.0, 30.0])

    def test_a_long_story_drops_the_weakest_beats_not_the_turns(self):
        p, pid, _ = project()
        orig = music_timing.PROMPT_MAX
        try:
            music_timing.PROMPT_MAX = 1100
            b = music_timing.brief(p, pid)
        finally:
            music_timing.PROMPT_MAX = orig
        self.assertLessEqual(len(b["prompt"]), 1100)
        self.assertIn("exactly at its time", b["prompt"])
        self.assertTrue(any("shock" in x for x in b["beats"]))              # priority 1 kept


if __name__ == "__main__":
    unittest.main()
