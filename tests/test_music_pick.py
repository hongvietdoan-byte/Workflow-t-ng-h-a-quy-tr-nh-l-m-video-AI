"""Bố cục điểm 8 (người dùng 07/10, Khủng Long Đỏ): nhạc chỉ vào được qua ô chọn tệp (trình duyệt không tải lên được → phải chép tay vào
data/projects/22/music). Nay chọn được từ Kho âm thanh (nhạc), bản nhạc AI đã tạo của dự án, và thư mục `nhac_rieng` của dự án."""
import os
import shutil
import tempfile
import unittest

from core import music
from core.db import connect
from core.pipeline import Pipeline


class PickTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("x")
        lib = os.path.join(self.dir, "kho")
        os.makedirs(lib)
        self.song = os.path.join(lib, "dance.mp3")
        open(self.song, "wb").write(b"ID3kho")
        c = self.p.conn
        c.execute("INSERT INTO sound_sources (id, path) VALUES (1, ?)", (lib,))
        c.execute("INSERT INTO sounds (source_id, path, name, category, kind, search, ext, size) VALUES (1, ?, 'Dance song', 'Nhạc', 'music',"
                  " 'dance song', '.mp3', 6)", (self.song,))
        c.execute("INSERT INTO sounds (source_id, path, name, category, kind, search, ext, size) VALUES (1, ?, 'Boom', 'SFX', 'sfx',"
                  " 'boom', '.wav', 6)", (os.path.join(lib, "boom.wav"),))
        c.commit()
        own = music.own_dir(self.dir, self.pid)
        open(os.path.join(own, "nhac_goc_34s.m4a"), "wb").write(b"m4a")

    def test_lists_library_music_and_the_project_folder_never_sound_effects(self):
        items = music.pick_sources(self.p.conn, self.dir, self.pid)
        labels = [i["label"] for i in items]
        self.assertTrue(any("Dance song" in l and "Kho" in l for l in labels), labels)
        self.assertTrue(any("nhac_goc_34s.m4a" in l for l in labels), labels)
        self.assertFalse(any("Boom" in l for l in labels))
        self.assertEqual(len(music.pick_sources(self.p.conn, self.dir, self.pid, "dance")), 1)       # search narrows the Kho part

    def test_using_one_as_background_or_second_music(self):
        items = {i["label"]: i for i in music.pick_sources(self.p.conn, self.dir, self.pid)}
        kho = next(i for l, i in items.items() if "Dance song" in l)
        music.use_pick(self.p, self.dir, self.pid, kho["path"], second=False)
        self.assertEqual(os.listdir(music.project_dirs(self.dir, self.pid)[1]), ["selected.mp3"])
        self.assertTrue(os.path.exists(self.song))                                    # the original is never moved
        own = next(i for l, i in items.items() if "nhac_goc" in l)
        music.use_pick(self.p, self.dir, self.pid, own["path"], second=True)
        from core import delivery
        self.assertEqual(os.listdir(delivery.second_music_dir(self.dir, self.pid)), ["second.m4a"])

    def test_a_missing_file_is_said(self):
        with self.assertRaises(ValueError):
            music.use_pick(self.p, self.dir, self.pid, os.path.join(self.dir, "khong_co.mp3"), second=False)


if __name__ == "__main__":
    unittest.main()


class ScreenTests(unittest.TestCase):
    def test_the_delivery_screen_picks_music_from_the_project_folder(self):
        from streamlit.testing.v1 import AppTest
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        data = os.path.join(tmp, "projects")
        for k, v in (("PIPELINE_DB", os.path.join(tmp, "m.sqlite")), ("PIPELINE_DATA", data), ("KNOWLEDGE_USER_DIR", os.path.join(tmp, "ku"))):
            os.environ[k] = v
            self.addCleanup(os.environ.pop, k, None)
        p = Pipeline(connect(os.environ["PIPELINE_DB"]))
        pid = p.create_project("x")
        p.create_scene(pid, 1, "CẢNH 1")
        open(os.path.join(music.own_dir(data, pid), "nhac.mp3"), "wb").write(b"ID3")
        at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py"), default_timeout=30)
        at.session_state["step"] = "Bản giao"
        at.run()
        self.assertFalse(at.exception, [e.value for e in at.exception])
        next(b for b in at.button if b.key == f"mpick_go_{pid}_1").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(os.listdir(music.project_dirs(data, pid)[1]), ["selected.mp3"])

