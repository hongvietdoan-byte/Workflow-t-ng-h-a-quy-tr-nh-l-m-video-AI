"""GĐ7 (kế hoạch V4): regressions for the faults an independent review found in the GĐ4 after-work (each test fails on the code
before the fix)."""
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from core import color_match, delivery, lineage, llm_io, voice
from core.db import connect
from core.pipeline import Pipeline


class ReviewTests(unittest.TestCase):
    def test_a_voice_direction_change_does_not_redo_the_clip(self):
        base = {"text": "x", "dialogue": [{"speaker": "KELLY", "text": "Em hiểu rồi…"}]}
        directed = {"text": "x", "dialogue": [{"speaker": "KELLY", "text": "Em hiểu rồi…", "delivery": {"pace": "slow"}}]}
        self.assertEqual(lineage.motion_spec_hash(base), lineage.motion_spec_hash(directed))
        changed = {"text": "x", "dialogue": [{"speaker": "KELLY", "text": "Em hiểu."}]}
        self.assertNotEqual(lineage.motion_spec_hash(base), lineage.motion_spec_hash(changed))      # the words still count

    def test_two_identical_lines_keep_their_own_direction(self):
        p = Pipeline(connect())
        pid = p.create_project("same words")
        sid = p.create_scene(pid, 1, "s")
        lines = [{"speaker": "KELLY", "text": "Đi thôi.", "delivery": {"emotion": "happy"}},
                 {"speaker": "MAXIM", "text": "Đi thôi.", "delivery": {"emotion": "scared", "tag": "whispers"}}]
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "x", "dialogue": lines}, ensure_ascii=False), sid))
        p.conn.commit()
        changed = llm_io.update_scene(p, pid, 1, {"dialogue": [{"speaker": d["speaker"], "text": d["text"]} for d in lines]})
        data = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])
        self.assertEqual([d["delivery"] for d in data["dialogue"]], [lines[0]["delivery"], lines[1]["delivery"]])
        self.assertNotIn("dialogue", changed)                                     # saving unchanged lines changes nothing

    def test_switching_voice_direction_off_again_keeps_the_directed_voices(self):
        from core import audio_lib
        p = Pipeline(connect())
        pid = p.create_project("voice")
        sid = p.create_scene(pid, 1, "s")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1, "dialogue": [
            {"speaker": "KELLY", "text": "Em hiểu rồi, anh đi đi…", "delivery": {"pace": "slow"}}]}, ensure_ascii=False), sid))
        p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'KELLY', '')", (pid,))
        voice.set_profile(p.conn, pid, "KELLY", {"voice_id": 71, "voice_name": "Kelly"})
        calls = []

        class Prov:
            def generate_tts(self, text, vid, model, lang, name="tts", params=None):
                calls.append(text)
                return str(len(calls))
        data = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, {"FEATURE_VOICE_DIRECTION": "1"}):
            voice.generate(p.conn, pid, Prov(), data, ledger=False)
        directory = audio_lib.assets_dir(data, pid)
        items = audio_lib.load(directory)
        items[0]["state"] = "succeeded"
        audio_lib._save(directory, items)
        with mock.patch.dict(os.environ, {"FEATURE_VOICE_DIRECTION": "0"}):
            voice.generate(p.conn, pid, Prov(), data, ledger=False)
        self.assertEqual(len(calls), 1)                                           # not paid a second time

    def test_hit_words_are_whole_words(self):
        from core import audio_lib
        d = tempfile.mkdtemp()
        entry = lambda label, t: {"kind": "sound_effect", "label": label, "start": t, "use": True, "state": "succeeded"}  # noqa: E731
        audio_lib._save(d, [entry("nước nổi bọt", 1.0), entry("Cymbal crash", 2.0), entry("đập cánh", 3.0), entry("tiếng nổ lớn", 4.0),
                            entry("AI: body fall impact", 5.0)])
        self.assertEqual(delivery.impact_times(d), [4.0, 5.0])

    def test_a_shot_without_scene_or_sequence_is_never_colour_grouped(self):
        p = Pipeline(connect())
        pid = p.create_project("old v2")
        rows = []
        for idx in (1, 2):
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"location": "tháp", "size": "WS"}), sid))
            rows.append({"scene_id": sid, "idx": idx})
        p.conn.commit()
        self.assertEqual(color_match.groups(p.conn, pid, rows), [])

    def test_the_render_manifest_lists_the_original_clips_when_colour_matched(self):
        from core import final_cut, ffmpeg_studio
        try:
            ff = ffmpeg_studio.find_ffmpeg()
        except ffmpeg_studio.FFmpegNotFound:
            self.skipTest("no ffmpeg")
        data = tempfile.mkdtemp()
        p = Pipeline(connect())
        pid = p.create_project("render", aspect="9:16")
        for idx, colour in ((1, "0x808080"), (2, "0x8c8074")):              # the 2nd under a warmer light: it will be matched
            sid = p.create_scene(pid, idx, f"s{idx}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": 1, "shot_no": idx, "size": "MS",
                                                                              "location": "tháp"}), sid))
            path = final_cut.clip_path(data, pid, idx)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={colour}:s=270x480:d=1.5", "-vf",
                            "drawbox=y=0:w=270:h=40:color=black:t=fill,drawbox=y=440:w=270:h=40:color=white:t=fill",
                            "-pix_fmt", "yuv420p", path], check=True)
        p.conn.commit()
        with mock.patch.dict(os.environ, {"FEATURE_SHOT_COLOR_MATCH": "1"}):
            res = delivery.render(p, pid, data, music_path=None)
        man = json.loads(p.conn.execute("SELECT manifest FROM outputs WHERE id=?", (res["output_id"],)).fetchone()["manifest"])
        self.assertTrue(any(c.get("fixed") for c in man["color_match"]))
        self.assertFalse(any("match_" in json.dumps(c) for c in man["clips"]))   # lineage follows the shots' own clips


if __name__ == "__main__":
    unittest.main()
