"""D1 J-cut, D6 music breath before a turn, D13 viewer check sheet (knowledge/editor/editing.md E1, E4, E9)."""
import json
import os
import subprocess
import tempfile
import unittest
import wave
from unittest import mock

import numpy as np

from core import ffmpeg_studio, viewer_check


def _ff():
    try:
        return ffmpeg_studio.find_ffmpeg()
    except ffmpeg_studio.FFmpegNotFound:
        raise unittest.SkipTest("no ffmpeg")


class BreathTests(unittest.TestCase):
    def test_the_music_goes_quiet_just_before_the_turn(self):
        ff = _ff()
        d = tempfile.mkdtemp()
        src, out = os.path.join(d, "m.wav"), os.path.join(d, "o.wav")
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=4", src], check=True)
        chain = "volume=1" + ffmpeg_studio.breath_filter([2.0])
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", src, "-af", chain, out], check=True)
        with wave.open(out) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
        rms = lambda a, b: float(np.sqrt(np.mean(x[int(a * sr):int(b * sr)] ** 2)))  # noqa: E731
        self.assertLess(rms(1.5, 1.95), rms(0.5, 1.2) * 0.1)                   # ~-26 dB in the 0,6 s before the turn
        self.assertGreater(rms(2.1, 2.8), rms(0.5, 1.2) * 0.8)                 # back on the turn
        self.assertEqual(ffmpeg_studio.breath_filter([]), "")

    def test_the_twist_is_found_on_the_render_timeline(self):
        from core import delivery
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("twist")
        for idx, heading in ((1, "CẢNH 1 – 0–8 GIÂY"), (2, "TWIST – 44–50 GIÂY")):
            p.conn.execute("INSERT INTO story_scenes (project_id, idx, heading, text, data) VALUES (?,?,?,?,?)", (pid, idx, heading, "", "{}"))
        rows = []
        for idx, sc in ((1, 1), (2, 1), (3, 2)):
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": sc, "shot_no": idx}), sid))
            rows.append({"scene_id": sid, "path": f"{idx}.mp4"})
        p.conn.commit()
        self.assertEqual(delivery.twist_times(p, pid, rows, [3.0, 2.5, 4.0]), [5.5])
        self.assertEqual(delivery.twist_times(p, pid, rows, [3.0, 2.5, 4.0], "crossfade", 0.5), [4.5])


class JCutTests(unittest.TestCase):
    def _items(self, data):
        from core import audio_lib
        return audio_lib.load(audio_lib.assets_dir(data, self.pid))

    def test_a_new_speaker_comes_in_before_the_cut_only_with_the_feature(self):
        from core import audio_lib, voice
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        self.pid = pid = p.create_project("j")
        data = tempfile.mkdtemp()
        sids = [p.create_scene(pid, i, f"s{i}") for i in (1, 2)]
        directory = audio_lib.assets_dir(data, pid)
        os.makedirs(directory, exist_ok=True)
        clips = []
        for i, (sid, who) in enumerate(zip(sids, ("KELLY", "KENTA")), 1):
            audio_lib._save(directory, audio_lib.load(directory) + [
                {"kind": "tts", "scene_id": sid, "line": 1, "speaker": who, "state": "succeeded", "file": f"t{i}.mp3",
                 "duration_ms": 1000, "dialogue": True, "label": who}])
            clips.append(os.path.join(data, f"{i}.mp4"))
        rows = [{"idx": i, "scene_id": sid, "path": c, "requested_sec": 3.0, "usable": True} for i, (sid, c) in enumerate(zip(sids, clips), 1)]
        with mock.patch("core.final_cut.collect_clips_for_render", return_value=rows):
            with mock.patch.dict(os.environ, {"FEATURE_J_CUT": "0"}):
                voice.place_on_timeline(p.conn, pid, data, durations=[3.0, 3.0])
                starts = [e["start"] for e in self._items(data)]
            self.assertEqual(starts, [voice.LEAD, 3.0 + voice.LEAD])
            with mock.patch.dict(os.environ, {"FEATURE_J_CUT": "1"}):
                voice.place_on_timeline(p.conn, pid, data, durations=[3.0, 3.0])
                starts = [e["start"] for e in self._items(data)]
            self.assertEqual(starts, [voice.LEAD, 3.0 - voice.J_LEAD])            # Kenta heard 0,25 s before his shot


class RealRenderTests(unittest.TestCase):
    """delivery.render end to end with real ffmpeg clips — a helper put under the render lock by mistake (GĐ4 after-work, e0c82ad)
    broke "▶ Dựng video cuối" while every test passed, because no test rendered for real."""

    def test_render_measures_loudness_and_colour_and_writes_the_file(self):
        from core import delivery, final_cut
        from core.db import connect
        from core.pipeline import Pipeline
        ff = _ff()
        data = tempfile.mkdtemp()
        p = Pipeline(connect())
        pid = p.create_project("render", aspect="9:16")
        for idx, colour in ((1, "0x808080"), (2, "0x998066")):
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?",
                           (json.dumps({"story_scene": 1, "shot_no": idx, "size": "MS", "location": "tháp"}), sid))
            path = final_cut.clip_path(data, pid, idx)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={colour}:s=270x480:d=1.5", "-f", "lavfi",
                            "-i", "sine=frequency=440:duration=1.5", "-shortest", "-pix_fmt", "yuv420p", "-c:a", "aac", path], check=True)
        p.conn.commit()
        settings = dict(delivery.get_settings(p, pid), keep_audio=True)
        res = delivery.render(p, pid, data, music_path=None, settings=settings)
        self.assertTrue(os.path.exists(res["path"]))
        man = json.loads(p.conn.execute("SELECT manifest FROM outputs WHERE id=?", (res["output_id"],)).fetchone()["manifest"])
        self.assertIsNotNone(man["loudness"]["lufs"])
        self.assertEqual(len(man["color_match"]), 1)                              # shot 2 measured against shot 1


class ViewerCheckTests(unittest.TestCase):
    def test_faces_under_the_app_bands_are_named(self):
        self.assertEqual(viewer_check.hidden_faces([(0.02, 0.12)]), ["top"])
        self.assertEqual(viewer_check.hidden_faces([(0.30, 0.45)]), [])
        self.assertEqual(viewer_check.hidden_faces([(0.70, 0.85)]), ["bottom"])

    def test_a_sheet_is_made_from_a_video(self):
        ff = _ff()
        d = tempfile.mkdtemp()
        video = os.path.join(d, "v.mp4")
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=s=270x480:d=2", "-pix_fmt", "yuv420p", video],
                       check=True)
        res = viewer_check.sheet(video, os.path.join(d, "sheet.png"), ff, count=4)
        self.assertTrue(os.path.exists(res["path"]))
        self.assertEqual(len(res["frames"]), 4)


if __name__ == "__main__":
    unittest.main()
