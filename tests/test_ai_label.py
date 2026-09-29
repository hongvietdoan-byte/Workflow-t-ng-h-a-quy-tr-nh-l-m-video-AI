"""S0.14 T6 (người dùng duyệt 2026-09-29): the "nội dung có dùng AI" label layer — feature `ai_label`, off by default."""
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from PIL import Image

from core import delivery, ffmpeg_studio
from core.db import connect
from core.pipeline import Pipeline


def make_video(path, w=360, h=640, seconds=1.5):
    subprocess.run([ffmpeg_studio.find_ffmpeg(), "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x808080:s={w}x{h}:d={seconds}",
                    "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", path], check=True)
    return path


def first_frame(video, png):
    subprocess.run([ffmpeg_studio.find_ffmpeg(), "-y", "-v", "error", "-i", video, "-frames:v", "1", png], check=True)
    return Image.open(png).convert("RGB")


class AiLabelTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("ai", aspect="9:16")
        out = os.path.join(delivery.output_dir(self.data, self.pid), "FINAL_VIDEO.mp4")
        make_video(out)
        self.final_id = delivery.record(self.p, self.pid, "final", out, None, {})

    def test_off_by_default_makes_nothing(self):
        with mock.patch.dict(os.environ, {"FEATURE_AI_LABEL": "0"}):
            self.assertIsNone(delivery.ai_label_layer(self.p, self.pid, self.data))

    def test_on_draws_the_label_top_left_and_keeps_the_sound(self):
        with mock.patch.dict(os.environ, {"FEATURE_AI_LABEL": "1", "AI_LABEL_TEXT": ""}):
            made = delivery.ai_label_layer(self.p, self.pid, self.data)
            self.assertTrue(made["video"].endswith("FINAL_VIDEO_ai.mp4"))
            self.assertTrue(ffmpeg_studio.has_audio(made["video"]))
            img = first_frame(made["video"], os.path.join(self.data, "f.png"))
            corner, middle = img.getpixel((22, 22)), img.getpixel((180, 320))
            self.assertLess(sum(corner), sum(middle) - 60)            # dark box over the grey frame in the corner only
            self.assertEqual(delivery.latest_layer(self.p, self.pid)["kind"], "ailabel")
            st = delivery.status(self.p, self.pid, self.data)
            self.assertIn("ailabel", [x["kind"] for x in st["layers"]])
            self.assertIsNone(next(x for x in st["layers"] if x["kind"] == "ailabel")["stale"])
        with mock.patch.dict(os.environ, {"FEATURE_AI_LABEL": "1", "AI_LABEL_TEXT": "AI-generated content"}):
            st = delivery.status(self.p, self.pid, self.data)
            self.assertEqual(next(x for x in st["layers"] if x["kind"] == "ailabel")["stale"], "chữ nhãn AI đã đổi")

    def test_default_text_and_env_text(self):
        with mock.patch.dict(os.environ, {"AI_LABEL_TEXT": ""}):
            self.assertEqual(delivery.ai_label_text(), "Nội dung có sử dụng AI")
        with mock.patch.dict(os.environ, {"AI_LABEL_TEXT": "  Made with AI "}):
            self.assertEqual(delivery.ai_label_text(), "Made with AI")

    def test_crop_export_redraws_the_label(self):
        with mock.patch.dict(os.environ, {"FEATURE_AI_LABEL": "1", "AI_LABEL_TEXT": ""}):
            delivery.ai_label_layer(self.p, self.pid, self.data)
            res = delivery.export_layer(self.p, self.pid, self.data, {"w": 360, "h": 360, "fit": "crop"})
        img = first_frame(res["path"], os.path.join(self.data, "e.png"))
        self.assertLess(sum(img.getpixel((16, 16))), sum(img.getpixel((180, 250))) - 60)



class OutputsMigrationTest(unittest.TestCase):
    def test_old_database_gains_ailabel_and_keeps_rows(self):
        import sqlite3
        path = os.path.join(tempfile.mkdtemp(), "old.sqlite")
        c = sqlite3.connect(path)
        c.executescript("""CREATE TABLE outputs (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('final','subtitle','endcard','export')), path TEXT NOT NULL,
            parent_id INTEGER REFERENCES outputs(id), manifest TEXT NOT NULL, created_at TEXT NOT NULL, created_by TEXT);
            INSERT INTO outputs VALUES (1, 7, 'final', 'a.mp4', NULL, '{}', 't', 'u');
            INSERT INTO outputs VALUES (2, 7, 'subtitle', 'b.mp4', 1, '{}', 't', 'u');""")
        c.commit()
        c.close()
        conn = connect(path)
        rows = [tuple(r) for r in conn.execute("SELECT id, kind, parent_id FROM outputs ORDER BY id")]
        self.assertEqual(rows, [(1, "final", None), (2, "subtitle", 1)])
        conn.execute("INSERT INTO outputs (project_id, kind, path, parent_id, manifest, created_at) VALUES (7,'ailabel','c.mp4',2,'{}','t')")
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
