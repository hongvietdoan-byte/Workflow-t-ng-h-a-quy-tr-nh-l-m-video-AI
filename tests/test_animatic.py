"""S2.4 (kế hoạch sau #8): the animatic at the storyboard gate — the film cut from its storyboard pictures, locked seconds, voices and
music, before any video is paid for (0 USD). Real trial 2026-09-29 on #8: 33 shots, 63.7 s, 23 lines, music, subtitles, ~40 s."""
import json
import unittest

from core import animatic, audio_lib, voice
from core.ffmpeg_studio import probe_duration
from core.music import MockAudioProvider
from tests.test_v2 import Base


class AnimaticTests(Base):
    def test_every_camera_move_gives_a_filter_and_a_still_move_stays_put(self):
        for move in ("static", "push_in", "pull_out", "pan", "pan_left", "tilt", "truck", "orbit", "unknown"):
            f = animatic.move_filter(move, 48, 720, 1280)
            self.assertIn("zoompan=", f)
            self.assertIn("s=720x1280", f)
        self.assertIn("z='1.0'", animatic.move_filter("static", 48, 720, 1280))
        self.assertIn("on/48", animatic.move_filter("push_in", 48, 720, 1280))

    def test_the_animatic_follows_the_shot_seconds_and_says_what_is_missing(self):
        for r in self.p.conn.execute("SELECT id, data FROM scenes WHERE project_id=?", (self.pid,)).fetchall():
            d = json.loads(r["data"] or "{}")
            d["duration_s"] = 1.5
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), r["id"]))
        self.p.conn.commit()
        n = self.p.conn.execute("SELECT COUNT(*) c FROM scenes WHERE project_id=?", (self.pid,)).fetchone()["c"]
        r = animatic.build(self.p, self.pid, self.data, with_music=False, with_subtitles=False)   # no picture yet: dark cards
        self.assertEqual(len(r["missing"]), n)
        self.assertAlmostEqual(probe_duration(r["path"]), 1.5 * n, delta=0.3)
        self.approve_images()
        r = animatic.build(self.p, self.pid, self.data, with_music=False, with_subtitles=False)
        self.assertEqual(r["missing"], [])

    def test_voice_lines_fall_inside_their_shot_in_order(self):
        for name in ("KENTA", "KELLY", "MAXIM"):
            voice.set_profile(self.p.conn, self.pid, name, {"voice_id": 1, "voice_name": "Mock"})
        audio = MockAudioProvider()
        voice.generate(self.p.conn, self.pid, audio, self.data)
        audio_lib.refresh(audio, audio_lib.assets_dir(self.data, self.pid))
        film = animatic.shots(self.p, self.pid, self.data)
        extras = animatic.voice_extras(self.data, self.pid, film)
        starts, t = {}, 0.0
        for s in film:
            starts[s["scene_id"]] = (t, t + s["seconds"])
            t += s["seconds"]
        self.assertTrue(extras)
        self.assertEqual([e["start"] for e in extras], sorted(e["start"] for e in extras))
        self.assertTrue(all(any(a <= e["start"] < b for a, b in starts.values()) for e in extras))


if __name__ == "__main__":
    unittest.main()
