"""N3 (người dùng chốt 08/10): nhạc nền theo ĐƯỜNG CẢM XÚC của cả câu chuyện — các chặng mở đầu → căng → ngoặt → cao trào → kết (một chặng
qua nhiều cảnh), giây đổi chặng = giây bước ngoặt trên bản dựng thật, ưu tiên MỘT bản nhạc AI liền mạch; chỉ tách bài khi đổi hẳn chất
liệu (bài gốc của đoạn nhảy), nối mượt; điểm vào bài tự động; ducking 8–12 dB đo bằng tín hiệu tổng hợp. Cờ `music_story_arc` tắt =
hành vi cũ."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import delivery, ffmpeg_studio, music_cues, music_fit, music_timing
from core.db import connect
from core.pipeline import Pipeline

HEADS = {1: "MỞ ĐẦU — sáng ở đảo", 2: "CĂNG THẲNG — bị bám đuôi", 3: "Căng thẳng leo thang", 4: "TWIST — đồng đội là gián điệp",
         5: "CAO TRÀO — trận cuối", 6: "KẾT — chiến thắng"}
SHOTS = [  # (story_scene, seconds, extra)
    (1, 4.0, {"mood": "bình yên"}), (1, 3.0, {"mood": "bình yên"}),
    (2, 5.0, {"mood": "hồi hộp"}), (3, 4.0, {"mood": "khẩn cấp"}), (3, 2.0, {"mood": "khẩn cấp"}),
    (4, 3.0, {"mood": "vỡ lẽ"}), (5, 6.0, {"mood": "khẩn cấp", "performance": {"intensity": 5}}), (6, 4.0, {"mood": "ấm áp"}),
]
ON = {"FEATURE_MUSIC_STORY_ARC": "1"}


def project(shots=SHOTS, heads=HEADS, director=None):
    p = Pipeline(connect())
    pid = p.create_project("arc")
    for idx, h in heads.items():
        p.conn.execute("INSERT INTO story_scenes (project_id, idx, heading, text, data) VALUES (?,?,?,?,?)", (pid, idx, h, "", "{}"))
    ids = []
    for i, (sc, secs, extra) in enumerate(shots, 1):
        sid = p.create_scene(pid, i, f"s{i}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": sc, "duration_s": secs, **extra}), sid))
        ids.append(sid)
    if director is not None:
        p.conn.execute("UPDATE projects SET director_raw=? WHERE id=?", (json.dumps(director), pid))
    p.conn.commit()
    return p, pid, ids


class ArcPlanTests(unittest.TestCase):
    def test_chapters_follow_the_story_turns_not_the_shots(self):
        p, pid, _ = project()
        a = music_cues.plan(p, pid)
        self.assertEqual([c["stage"] for c in a["chapters"]], ["open", "build", "turn", "climax", "end"])
        build = a["chapters"][1]
        self.assertEqual(build["scenes"], [2, 3])                       # one chapter over two script scenes / three clips
        self.assertEqual((build["start"], build["end"]), (7.0, 18.0))
        self.assertEqual(a["turns"], [7.0, 18.0, 21.0, 27.0])          # 8 shots, 6 scenes -> 4 turns of the story
        self.assertEqual(a["source"], "heading")
        self.assertEqual(len(a["tracks"]), 1)                           # one continuous AI piece

    def test_the_directors_arc_wins(self):
        p, pid, _ = project(director={"music": {"arc": [{"stage": "open", "scene": 1}, {"stage": "build", "scene": 2},
                                                        {"stage": "climax", "scene": 4}, {"stage": "end", "scene": 6}]}})
        a = music_cues.plan(p, pid)
        self.assertEqual(a["source"], "director")
        self.assertEqual([(c["stage"], c["scenes"]) for c in a["chapters"]],
                         [("open", [1]), ("build", [2, 3]), ("climax", [4, 5]), ("end", [6])])

    def test_without_headings_the_position_and_peak_decide(self):
        p, pid, _ = project(heads={k: "" for k in HEADS})
        a = music_cues.plan(p, pid)
        self.assertEqual(a["source"], "position")
        self.assertEqual(a["chapters"][0]["stage"], "open")
        self.assertEqual(a["chapters"][-1]["stage"], "end")
        self.assertIn("climax", [c["stage"] for c in a["chapters"]])   # the intensity-5 shot

    def test_turns_on_the_render_land_on_a_downbeat_and_follow_crossfades(self):
        p, pid, _ = project()
        a = music_cues.plan(p, pid, overlap=0.5)
        self.assertEqual(a["chapters"][1]["start"], 6.0)               # 2 shots before it, 0,5 s crossfade after the first
        b = music_cues.plan(p, pid, beats=[6.8, 17.7, 21.6, 26.0])
        self.assertEqual(b["turns"], [6.8, 17.7, 21.0, 27.0])          # snapped within 0,5 s only
        self.assertTrue(b["chapters"][1]["snapped"])

    def test_music_enters_by_itself_where_the_director_lets_it(self):
        shots = [(1, 3.0, {"sound": {"music": "cut"}}), (1, 2.0, {"sound": {"music": "in"}})] + SHOTS[2:]
        p, pid, _ = project(shots=shots)
        self.assertEqual(music_cues.plan(p, pid)["enter"], 3.0)          # #22 set 1,8 s by hand
        p2, pid2, _ = project()
        self.assertEqual(music_cues.plan(p2, pid2)["enter"], 0.0)


class ArcBriefTests(unittest.TestCase):
    def test_flag_off_is_the_old_brief(self):
        p, pid, _ = project()
        with mock.patch.dict(os.environ, {"FEATURE_MUSIC_STORY_ARC": "0"}):
            b = music_timing.timed_brief(p, pid)
        self.assertEqual(b["prompt"], music_timing.brief(p, pid)["prompt"])
        self.assertNotIn("arc", b)
        self.assertEqual(len(b["turns"]), 5)                            # every script scene

    def test_one_piece_with_each_chapter_and_its_second(self):
        p, pid, _ = project()
        with mock.patch.dict(os.environ, ON):
            b = music_timing.timed_brief(p, pid)
        text = b["prompt"]
        self.assertIn("ONE continuous piece", text)
        self.assertEqual(b["turns"], [7.0, 18.0, 21.0, 27.0])
        for word in ("opening", "rising tension", "the turn", "climax", "ending"):
            self.assertIn(word, text)
        self.assertIn("0:18.0", text)
        self.assertEqual(music_fit.planned(text)["turns"], b["turns"])     # music_fit still reads the change seconds back
        self.assertLessEqual(len(text), music_timing.PROMPT_MAX)
        self.assertEqual(b["drafts"], music_cues.DRAFTS)


class TracksTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_a_song_part_is_its_own_track_joined_smoothly(self):
        shots = list(SHOTS)
        shots[6] = (5, 6.0, {"mood": "khẩn cấp", "sound": {"music_source": "song"}})
        p, pid, _ = project(shots=shots)
        a = music_cues.plan(p, pid)
        self.assertEqual([t["material"] for t in a["tracks"]], ["score", "song", "score"])
        self.assertEqual(a["tracks"][1]["start"], 21.0)
        self.assertEqual(a["tracks"][1]["join"], "breath")              # the climax: a held breath before the song
        self.assertEqual(a["tracks"][2]["join"], "crossfade")

    def test_old_projects_render_and_hash_as_before(self):
        p, pid, _ = project()
        d2 = delivery.second_music_dir(self.dir, pid)
        open(os.path.join(d2, "song.wav"), "wb").close()
        settings = {**delivery.DEFAULTS, "music2_start": 18.08}
        before = delivery.audio_hash(self.dir, pid)
        with mock.patch.dict(os.environ, ON):
            self.assertEqual(delivery.audio_hash(self.dir, pid), before)        # no cues.json: same hash
            legacy = delivery.music_tracks(p, self.dir, pid, settings, [], [])
        self.assertEqual(legacy, [{"path": os.path.join(d2, "song.wav"), "start": 18.08, "join": "legacy"}])
        with mock.patch.dict(os.environ, {"FEATURE_MUSIC_STORY_ARC": "0"}):
            music_cues.save(self.dir, pid, [{"file": "x.wav"}])
            self.assertEqual(delivery.audio_hash(self.dir, pid), before)        # flag off: cues are not read
            self.assertEqual(delivery.music_tracks(p, self.dir, pid, settings, [], [])[0]["join"], "legacy")

    def test_cues_get_their_entry_point_from_the_story(self):
        shots = list(SHOTS)
        shots[6] = (5, 6.0, {"sound": {"music_source": "song"}})
        p, pid, ids = project(shots=shots)
        d = music_cues.cues_dir(self.dir, pid)
        open(os.path.join(d, "dance.wav"), "wb").close()
        music_cues.save(self.dir, pid, [{"file": "dance.wav"}])
        rows = [{"scene_id": s, "path": "c.mp4"} for s in ids]
        with mock.patch.dict(os.environ, ON):
            tr = delivery.music_tracks(p, self.dir, pid, dict(delivery.DEFAULTS), rows, [s[1] for s in shots])
            h = delivery.audio_hash(self.dir, pid)
        self.assertEqual(tr, [{"path": os.path.join(d, "dance.wav"), "start": 21.0, "join": "breath"}])   # not set by hand
        self.assertNotEqual(h, delivery.audio_hash(self.dir, pid))      # the cues are in the hash only when they are used


@unittest.skipUnless(shutil.which("ffmpeg") or os.environ.get("FFMPEG_PATH"), "cần ffmpeg")
class MixTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _tone(self, name, f, secs):
        path = os.path.join(self.dir, name)
        ffmpeg_studio.run([ffmpeg_studio.find_ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=f={f}:d={secs}:r=44100",
                           "-af", "volume=0.3", "-ac", "2", path])
        return path

    def test_tracks_are_joined_without_a_hole_or_with_the_planned_breath(self):
        a, b = self._tone("a.wav", 220, 20), self._tone("b.wav", 330, 20)
        for join, hole in (("crossfade", False), ("breath", True), ("cut", False)):
            out = os.path.join(self.dir, f"bed_{join}.wav")
            music_cues.assemble([{"path": a, "start": 0.0, "join": "enter"}, {"path": b, "start": 8.0, "join": join}], 16.0, out)
            self.assertAlmostEqual(ffmpeg_studio.probe_duration(out), 16.0, delta=0.1)
            quiet = music_cues.rms_db(out, 7.55, 7.85)
            self.assertEqual(quiet < -40, hole, f"{join}: {quiet} dB just before the change")
            self.assertAlmostEqual(music_cues.rms_db(out, 12, 14), music_cues.rms_db(b, 12, 14), delta=0.5)   # the new track, whole

    def test_ducking_presses_the_music_8_to_12_db_under_any_usual_voice(self):
        depths = {v: music_cues.duck_depth(v, ffmpeg_studio.DUCK_EVEN) for v in (-26, -22, -18, -14)}
        for v, dip in depths.items():
            self.assertTrue(8.0 <= dip <= 12.0, f"giọng {v} dBFS: nhạc hạ {dip} dB")
        self.assertLess(music_cues.duck_depth(-22, ffmpeg_studio.DUCK), 8.0)   # why the old setting is replaced under the flag
        with mock.patch.dict(os.environ, ON):
            self.assertEqual(ffmpeg_studio.duck_filter(), ffmpeg_studio.DUCK_EVEN)
        with mock.patch.dict(os.environ, {"FEATURE_MUSIC_STORY_ARC": "0"}):
            self.assertEqual(ffmpeg_studio.duck_filter(), ffmpeg_studio.DUCK)


if __name__ == "__main__":
    unittest.main()
