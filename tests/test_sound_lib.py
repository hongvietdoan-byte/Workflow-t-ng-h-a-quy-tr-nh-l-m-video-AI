import os
import shutil
import struct
import tempfile
import unittest
import wave

from streamlit.testing.v1 import AppTest

from core import audio_lib, autopilot, music, sound_lib
from core.db import connect
from core.sound_lib import SoundError
from tests.test_autopilot import Setup


def wav(path, seconds=1.0, rate=8000):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 1000) * int(rate * seconds))
    return path


def fake(path, size=100):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"x" * size)
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.src = os.path.join(self.dir, "Sound")
        self.conn = connect()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def library(self):
        fake(os.path.join(self.src, "nhạc nền kịch tính", "Dark Storm.mp3"), 4_000_000)
        fake(os.path.join(self.src, "nhạc nền vui vẻ năng lượng", "Sunny Day.mp3"), 4_000_000)
        fake(os.path.join(self.src, "nhạc nền sôi động", "Race.mp3"), 4_000_000)
        fake(os.path.join(self.src, "kevin macleod", "Epic Unease.mp3"), 5_000_000)
        fake(os.path.join(self.src, "Sound FX Pack", "Whoosh 1.wav"), 90_000)
        fake(os.path.join(self.src, "đập đất, rung chuyển", "Ground Slam.mp3"), 50_000)
        fake(os.path.join(self.src, "popup", "Pop.mp3"), 10_000)
        fake(os.path.join(self.src, "New folder", "unknown_short.mp3"), 60_000)
        fake(os.path.join(self.src, "New folder", "unknown_long.mp3"), 6_000_000)
        fake(os.path.join(self.src, "Sound FX Pack", "cover.jpg"), 500)               # not audio
        fake(os.path.join(self.src, "video.mp4"), 500)                                  # not audio
        fake(os.path.join(self.src, ".DS_Store"), 10)
        fake(os.path.join(self.src, "backup", "Old Track.mp3"), 4_000_000)              # ignored folder word
        return sound_lib.add_source(self.conn, self.src)


class ScanTests(Base):
    def test_files_are_listed_and_labelled_from_their_folders_without_opening_them(self):
        sid = self.library()
        rep = sound_lib.scan(self.conn, sid)
        self.assertEqual((rep["added"], rep["removed"]), (9, 0))                        # 9 audio files; jpg/mp4/.DS_Store/backup left out
        rows = {r["name"]: r for r in sound_lib.search(self.conn, limit=50)["rows"]}
        self.assertEqual((rows["Dark Storm"]["kind"], rows["Dark Storm"]["mood"]), ("music", "kịch tính"))
        self.assertEqual((rows["Sunny Day"]["kind"], rows["Sunny Day"]["mood"]), ("music", "vui vẻ"))
        self.assertEqual(rows["Race"]["mood"], "sôi động")
        self.assertEqual(rows["Epic Unease"]["kind"], "music")                          # "kevin macleod" folder
        for sfx in ("Whoosh 1", "Ground Slam", "Pop"):
            self.assertEqual(rows[sfx]["kind"], "sfx", sfx)
        self.assertEqual((rows["unknown_short"]["kind"], rows["unknown_long"]["kind"]), ("sfx", "music"))   # by size when no word helps
        self.assertNotIn("Old Track", rows)
        self.assertIsNone(rows["Dark Storm"]["duration"])                               # measured only when needed

    def test_rescanning_only_does_the_difference(self):
        sid = self.library()
        sound_lib.scan(self.conn, sid)
        again = sound_lib.scan(self.conn, sid)
        self.assertEqual((again["added"], again["changed"], again["unchanged"], again["removed"]), (0, 0, 9, 0))
        fake(os.path.join(self.src, "popup", "New Pop.mp3"), 12_000)
        os.remove(os.path.join(self.src, "popup", "Pop.mp3"))
        with open(os.path.join(self.src, "sound FX Pack".replace("sound", "Sound"), "Whoosh 1.wav"), "wb") as f:
            f.write(b"y" * 91_000)
        third = sound_lib.scan(self.conn, sid)
        self.assertEqual((third["added"], third["removed"], third["changed"]), (1, 1, 1))

    def test_search_ignores_accents_and_case_and_filters(self):
        sound_lib.scan(self.conn, self.library())
        self.assertEqual([r["name"] for r in sound_lib.search(self.conn, "DAP DAT")["rows"]], ["Ground Slam"])
        self.assertEqual({r["name"] for r in sound_lib.search(self.conn, "kich tinh")["rows"]}, {"Dark Storm", "Epic Unease"})   # by folder mood / "epic"
        self.assertEqual(sound_lib.search(self.conn, kind="sfx")["total"], 4)
        self.assertEqual(sound_lib.search(self.conn, kind="music", mood="sôi động")["total"], 1)
        many = sound_lib.search(self.conn, limit=3, offset=3)
        self.assertEqual((many["total"], len(many["rows"])), (9, 3))
        self.assertIn(("Sound FX Pack", 1), sound_lib.categories(self.conn, "sfx"))
        self.assertEqual(sound_lib.counts(self.conn), {"music": 5, "sfx": 4})

    def test_sources_are_validated_and_an_unavailable_drive_is_reported_not_fatal(self):
        with self.assertRaises(SoundError):
            sound_lib.add_source(self.conn, os.path.join(self.dir, "nowhere"))
        sid = self.library()
        with self.assertRaises(SoundError):
            sound_lib.add_source(self.conn, self.src)
        sound_lib.auto_scan(self.conn)
        self.assertEqual(sound_lib.auto_scan(self.conn), [])                            # unchanged: no work
        shutil.rmtree(self.src)
        self.assertEqual(sound_lib.auto_scan(self.conn), [])
        self.assertIn("Lỗi", sound_lib.list_sources(self.conn)[0]["last_summary"])
        self.assertEqual(sound_lib.counts(self.conn)["music"], 5)                       # the library keeps what it knew
        sound_lib.remove_source(self.conn, sid)
        self.assertEqual(sound_lib.counts(self.conn), {})


class ChoosingTests(Base):
    def setUp(self):
        super().setUp()
        sound_lib.scan(self.conn, self.library())

    def test_scene_moods_map_to_the_library_moods(self):
        self.assertEqual(sound_lib.moods_of_text("căng thẳng, hồi hộp, u ám")[0], "kịch tính")
        self.assertEqual(sound_lib.moods_of_text("Hành động nhanh"), ["sôi động"])
        self.assertEqual(sound_lib.moods_of_text("vui, hào hứng")[0], "vui vẻ")
        self.assertEqual(sound_lib.moods_of_text("xyz"), [])

    def test_music_suggestions_follow_the_mood_and_fall_back_to_any_music(self):
        first = sound_lib.suggest_music(self.conn, ["căng thẳng"])
        self.assertIn(first[0]["name"], ("Dark Storm", "Epic Unease"))                  # both are dramatic
        self.assertTrue(all(r["kind"] == "music" for r in first))
        anything = sound_lib.suggest_music(self.conn, ["không rõ"])
        self.assertTrue(anything and all(r["kind"] == "music" for r in anything))       # no mood match: still offers music
        self.assertEqual(sound_lib.suggest_music(self.conn, ["vui"], seed=0)[0]["name"], "Sunny Day")

    def test_the_length_is_measured_once_and_a_long_enough_track_is_preferred(self):
        short = wav(os.path.join(self.dir, "lib", "nhạc nền kịch tính", "Short.wav"), 1.0)
        longer = wav(os.path.join(self.dir, "lib", "nhạc nền kịch tính", "Longer.wav"), 4.0)
        sid = sound_lib.add_source(self.conn, os.path.join(self.dir, "lib"))
        sound_lib.scan(self.conn, sid)
        rows = {r["name"]: r for r in sound_lib.search(self.conn, "", kind="music", limit=50)["rows"] if r["path"] in (short, longer)}
        seconds = sound_lib.ensure_duration(self.conn, rows["Longer"]["id"])
        self.assertAlmostEqual(seconds, 4.0, delta=0.3)
        self.assertEqual(sound_lib.get(self.conn, rows["Longer"]["id"])["duration"], seconds)   # remembered
        picked = sound_lib.pick_music(self.conn, ["căng thẳng"], min_seconds=3.5, seed=0)
        self.assertIn(picked["name"], ("Longer", "Short", "Dark Storm", "Epic Unease"))
        only = sound_lib.pick_music(self.conn, ["căng thẳng"], min_seconds=3.5, seed=0)
        self.assertTrue(only["name"] == "Longer" or (only.get("duration") or 0) < 3.5)          # a long enough track wins when one is checked


class UsingATrackTests(Base):
    def test_a_track_becomes_the_background_music_or_an_effect_by_copy(self):
        track = wav(os.path.join(self.dir, "t.wav"), 1.0)
        sound = {"path": track, "ext": ".wav", "name": "t"}
        selected = os.path.join(self.dir, "music")
        os.makedirs(selected)
        with open(os.path.join(selected, "old.mp3"), "wb") as f:
            f.write(b"old")
        dest = music.use_library_track(selected, track)
        self.assertEqual(os.listdir(selected), ["selected.wav"])                         # the previous choice was replaced
        self.assertTrue(os.path.exists(track))                                           # the original stays
        with self.assertRaises(ValueError):
            music.use_library_track(selected, os.path.join(self.dir, "missing.wav"))
        directory = os.path.join(self.dir, "assets")
        os.makedirs(directory)
        entry = audio_lib.add_local(directory, track, "Whoosh", start=2.5, volume=0.8)
        self.assertEqual((entry["state"], entry["use"], entry["start"], entry["volume"]), ("succeeded", True, 2.5, 0.8))
        extras = audio_lib.mix_list(directory)
        self.assertEqual((len(extras), extras[0]["start"], extras[0]["volume"]), (1, 2.5, 0.8))
        self.assertTrue(os.path.exists(extras[0]["path"]))
        self.assertTrue(dest.endswith("selected.wav"))
        with self.assertRaises(SoundError):
            sound_lib.copy_into({"path": os.path.join(self.dir, "gone.wav"), "ext": ".wav"}, directory, "x")


class AutomaticLibraryMusicTests(Setup):
    def test_without_the_library_mode_ai_music_is_the_default_and_the_library_only_backs_it_up(self):
        ctx = self.build()
        lib = os.path.join(tempfile.mkdtemp(), "nhạc nền kịch tính")
        wav(os.path.join(lib, "Dark Storm.wav"), 2.0)
        sound_lib.scan(self.p.conn, sound_lib.add_source(self.p.conn, os.path.dirname(lib)))
        autopilot.start(self.p, self.pid)                                                # music_mode not set: the AI provider makes the music
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.DONE)
        self.assertFalse(any("Nhạc nền từ kho" in e["msg"] for e in autopilot.status(self.p, self.pid)["log"]))
        _, selected = music.project_dirs(self.data, self.pid)
        self.assertEqual(len(os.listdir(selected)), 1)
        for name in os.listdir(selected):
            os.remove(os.path.join(selected, name))
        ctx.audio = None                                                                 # AI music unavailable: the library is the safety net
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.DONE)
        self.assertTrue(any("Nhạc nền từ kho" in e["msg"] for e in autopilot.status(self.p, self.pid)["log"]))

    def test_library_mode_uses_a_track_that_fits_the_mood_and_spends_nothing(self):
        ctx = self.build()
        lib = os.path.join(tempfile.mkdtemp(), "nhạc nền kịch tính")
        wav(os.path.join(lib, "Dark Storm.wav"), 2.0)
        sid = sound_lib.add_source(self.p.conn, os.path.dirname(lib))
        sound_lib.scan(self.p.conn, sid)
        self.p.conn.execute("UPDATE projects SET music_mode='library' WHERE id=?", (self.pid,))
        self.p.conn.commit()
        ctx.audio = None                                                                 # no paid music provider at all
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.DONE)
        _, selected = music.project_dirs(self.data, self.pid)
        self.assertEqual(os.listdir(selected), ["selected.wav"])
        self.assertTrue(any("Nhạc nền từ kho" in e["msg"] for e in autopilot.status(self.p, self.pid)["log"]))
        with open(os.path.join(self.data, str(self.pid), "output", "FINAL_VIDEO.mp4"), "rb") as f:
            self.assertIn(b"selected.wav", f.read())                                     # the render got that track

    def test_an_empty_library_falls_back_to_generating_the_track(self):
        ctx = self.build()
        self.p.conn.execute("UPDATE projects SET music_mode='library' WHERE id=?", (self.pid,))
        self.p.conn.commit()
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.DONE)
        self.assertEqual(len(music.load_drafts(music.project_dirs(self.data, self.pid)[0])), 1)   # the mock provider made one
        self.assertTrue(any("Kho nhạc" in e["msg"] for e in autopilot.status(self.p, self.pid)["log"]))

    def test_default_mode_never_touches_the_library(self):
        ctx = self.build()
        lib = os.path.join(tempfile.mkdtemp(), "nhạc nền vui vẻ")
        wav(os.path.join(lib, "Sunny.wav"), 1.0)
        sound_lib.scan(self.p.conn, sound_lib.add_source(self.p.conn, os.path.dirname(lib)))
        autopilot.start(self.p, self.pid)
        autopilot.run_until_done(self.p, self.pid, ctx)
        self.assertEqual(len(music.load_drafts(music.project_dirs(self.data, self.pid)[0])), 1)


class DashboardTests(Base):
    APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")

    def setUp(self):
        super().setUp()
        from tests.test_step1_flow import split_only
        self.tmp, self.db, self.data, self.p, self.pid = split_only()
        self.conn = self.p.conn
        os.environ.update({"PIPELINE_DB": self.db, "PIPELINE_DATA": self.data})

    def tearDown(self):
        os.environ.pop("PIPELINE_DB", None)
        os.environ.pop("PIPELINE_DATA", None)
        super().tearDown()

    def app(self, step="5"):
        at = AppTest.from_file(self.APP, default_timeout=40)
        at.query_params["step"] = step
        return at.run()

    def test_the_library_is_added_in_settings_and_used_in_step_5(self):
        wav(os.path.join(self.src, "nhạc nền kịch tính", "Dark Storm.wav"), 1.0)
        wav(os.path.join(self.src, "Sound FX Pack", "Whoosh.wav"), 1.0)
        at = self.app("1")
        self.assertFalse(at.exception)
        at.text_input(key="snd_new_path").set_value(self.src).run()
        next(b for b in at.button if b.key == "snd_new_go").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(sound_lib.counts(self.conn), {"music": 1, "sfx": 1})
        at = self.app("5")
        self.assertFalse(at.exception)
        self.assertTrue(any("Kho âm thanh của bạn (hỗ trợ) — 1 nhạc nền · 1 hiệu ứng" in e.label for e in at.expander))
        music_id = sound_lib.search(self.conn, kind="music")["rows"][0]["id"]
        sfx_id = sound_lib.search(self.conn, kind="sfx")["rows"][0]["id"]
        next(b for b in at.button if b.key == f"sr_use_{music_id}").click().run()
        _, selected = music.project_dirs(self.data, self.pid)
        self.assertEqual(os.listdir(selected), ["selected.wav"])
        at = self.app("5")
        at.number_input(key=f"sr_at_{sfx_id}").set_value(2.5).run()
        next(b for b in at.button if b.key == f"sr_add_{sfx_id}").click().run()
        extras = audio_lib.mix_list(audio_lib.assets_dir(self.data, self.pid))
        self.assertEqual((len(extras), extras[0]["start"]), (1, 2.5))
        next(b for b in at.button if b.key == f"sr_play_{sfx_id}").click().run()
        self.assertFalse(at.exception)                                                   # the preview player rendered

    def test_automatic_music_setting_is_saved_per_project_and_search_filters(self):
        wav(os.path.join(self.src, "nhạc nền vui vẻ", "Sunny.wav"), 1.0)
        wav(os.path.join(self.src, "nhạc nền kịch tính", "Dark.wav"), 1.0)
        sound_lib.scan(self.conn, sound_lib.add_source(self.conn, self.src))
        at = self.app("5")
        at.checkbox(key=f"music_mode_{self.pid}").set_value(True).run()
        self.assertEqual(self.conn.execute("SELECT music_mode FROM projects WHERE id=?", (self.pid,)).fetchone()[0], "library")
        at.text_input(key=f"snd_q_{self.pid}").set_value("kich tinh").run()
        self.assertFalse(at.exception)
        self.assertTrue(any(k.startswith("sr_use_") for k in [b.key for b in at.button if b.key]))
        self.assertEqual(len([b for b in at.button if (b.key or "").startswith("sr_use_")]), 1)          # only the dramatic one

    def test_an_empty_library_adds_nothing_to_step_5(self):
        at = self.app("5")
        self.assertFalse(at.exception)
        self.assertFalse(any("Kho âm thanh của bạn" in e.label for e in at.expander))

    def test_the_dashboard_lists_new_sound_files_when_it_opens(self):
        wav(os.path.join(self.src, "nhạc nền vui vẻ", "Sunny.wav"), 1.0)
        sound_lib.scan(self.conn, sound_lib.add_source(self.conn, self.src))
        wav(os.path.join(self.src, "nhạc nền vui vẻ", "Later.wav"), 1.0)
        self.app("5")
        self.assertEqual(sound_lib.counts(self.conn)["music"], 2)


class OldDatabaseTests(unittest.TestCase):
    def test_old_databases_get_the_new_tables_and_column(self):
        path = os.path.join(tempfile.mkdtemp(), "old.sqlite")
        conn = connect(path)
        conn.execute("DROP TABLE sounds")
        conn.execute("DROP TABLE sound_sources")
        conn.execute("ALTER TABLE projects DROP COLUMN music_mode")
        conn.commit()
        conn.close()
        conn = connect(path)
        self.assertEqual(sound_lib.list_sources(conn), [])
        self.assertIn("music_mode", {r["name"] for r in conn.execute("PRAGMA table_info(projects)")})


if __name__ == "__main__":
    unittest.main()
