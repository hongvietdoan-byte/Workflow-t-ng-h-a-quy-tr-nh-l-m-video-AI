"""S9.6: the whole film on one timeline (shots, lines, music on/off, effects, subtitles) — read only, nothing generated."""
import tempfile
import unittest

from core import timeline_view
from core.db import connect
from core.pipeline import Pipeline


class TimelineViewTests(unittest.TestCase):
    def test_a_project_without_clips_has_an_empty_timeline(self):
        p = Pipeline(connect())
        pid = p.create_project("t")
        data = timeline_view.tracks(p, tempfile.mkdtemp(), pid)
        self.assertEqual((data["total"], data["shots"]), (0.0, []))

    def test_every_track_is_drawn_and_music_silence_is_marked(self):
        data = {"total": 10.0, "shots": [{"start": 0, "end": 5, "label": "01"}, {"start": 5, "end": 10, "label": "02"}],
                "voice": [{"start": 1, "end": 2.5, "label": "KELLY", "title": "Anh <thật> sao?"}],
                "music": [{"start": 0, "end": 4, "label": "nhạc"}], "music_off": [{"start": 4, "end": 10}],
                "sfx": [{"start": 6, "end": 6.5, "label": "Impact"}], "subs": [{"start": 1, "end": 2.5, "label": "KELLY", "title": "x"}]}
        out = timeline_view.html(data)
        for _, name, _ in timeline_view.TRACKS:
            self.assertIn(name, out)
        self.assertIn("nhạc tắt 4.0–10.0s", out)
        self.assertIn("&lt;thật&gt;", out)                     # text is escaped


if __name__ == "__main__":
    unittest.main()
