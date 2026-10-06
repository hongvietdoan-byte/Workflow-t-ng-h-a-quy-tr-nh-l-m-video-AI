"""S14.48 (ý 2 từ tài liệu 'Prompt Spider' 06/10): màu chính nhân vật đo bằng CODE (0 USD) — trích bảng màu vùng thân (dưới mặt) từ ảnh
tham chiếu đã duyệt, so với ảnh tạo ra; chỉ ghi chú 'uncertain' (ngưỡng chưa hiệu chỉnh trên ảnh thật), không tự từ chối; sau cờ
`palette_check` TẮT. Không có bộ dò mặt trên máy test → thay bằng hộp mặt cố định."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import features, palette
from core.db import connect

RED, BLUE, GRAY, SKIN = (192, 57, 43), (41, 98, 255), (128, 128, 128), (224, 172, 140)
FACE = (0.40, 0.10, 0.60, 0.30)          # left, top, right, bottom (fractions)


def picture(path, torso, size=(400, 600), face=FACE):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", size, GRAY)
    d = ImageDraw.Draw(im)
    w, h = size
    l, t, r, b = face
    d.rectangle([l * w, t * h, r * w, b * h], fill=SKIN)
    fw = (r - l) * w
    d.rectangle([l * w - 0.6 * fw, b * h, r * w + 0.6 * fw, min(h, b * h + 2.2 * (b - t) * h)], fill=torso)
    im.save(path)
    return path


class PaletteTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        p = mock.patch.object(palette, "_faces", lambda path: [FACE])
        p.start()
        self.addCleanup(p.stop)

    def test_hex_and_delta_e(self):
        self.assertEqual(palette.to_hex(RED), "#C0392B")
        self.assertEqual(palette.from_hex("#c0392b"), RED)
        self.assertLess(palette.delta_e(RED, (190, 60, 45)), 5)
        self.assertGreater(palette.delta_e(RED, BLUE), 50)
        with self.assertRaises(ValueError):
            palette.from_hex("đỏ")

    def test_extract_finds_the_torso_colour(self):
        ref = picture(os.path.join(self.dir, "ref.png"), RED)
        got = palette.extract(ref)
        self.assertTrue(got["colors"])
        top = got["colors"][0]
        self.assertLess(palette.delta_e(palette.from_hex(top["hex"]), RED), 10)
        self.assertGreater(top["share"], 0.4)

    def test_same_outfit_is_ok_other_colour_is_flagged_uncertain(self):
        pal = palette.extract(picture(os.path.join(self.dir, "ref.png"), RED))
        ok = palette.check(picture(os.path.join(self.dir, "same.png"), RED), pal)
        self.assertEqual((ok["status"], ok["missing"]), ("uncertain", []))
        self.assertIn("khớp", ok["note"])
        bad = palette.check(picture(os.path.join(self.dir, "blue.png"), BLUE), pal)
        self.assertEqual(bad["status"], "uncertain")                                    # chưa hiệu chỉnh: không bao giờ certain_fail
        self.assertTrue(bad["missing"])
        self.assertIn("lệch", bad["note"])

    def test_not_measurable_cases_say_why(self):
        pal = palette.extract(picture(os.path.join(self.dir, "ref.png"), RED))
        with mock.patch.object(palette, "_faces", lambda path: [FACE, (0.1, 0.1, 0.2, 0.2)]):
            two = palette.check(picture(os.path.join(self.dir, "two.png"), RED), pal)
        self.assertEqual(two["status"], "not_measurable")
        self.assertIn("mặt", two["note"])
        with mock.patch.object(palette, "_faces", lambda path: None):
            none = palette.check(os.path.join(self.dir, "two.png"), pal)
        self.assertEqual(none["status"], "not_measurable")
        self.assertEqual(palette.check(os.path.join(self.dir, "two.png"), {"colors": []})["status"], "not_measurable")


class StoreAndAttachTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        for p in (mock.patch.object(palette, "_faces", lambda path: [FACE]),):
            p.start()
            self.addCleanup(p.stop)
        self.conn = connect()
        self.conn.execute("INSERT INTO projects (name, created_at) VALUES ('p', '2026-10-06T00:00:00Z')")
        self.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (1, 'KELLY', 'nữ')")
        self.conn.commit()
        self.ref = picture(os.path.join(self.dir, "ref.png"), RED)
        link = mock.patch.object(palette, "_reference_path", lambda conn, pid, name: self.ref if name == "KELLY" else None)
        link.start()
        self.addCleanup(link.stop)

    def test_flag_exists_and_is_off(self):
        self.assertIn("palette_check", features.FEATURES)
        self.assertFalse(features.FEATURES["palette_check"]["verified"])

    def test_palette_is_extracted_once_per_reference_and_stored(self):
        pal = palette.character_palette(self.conn, 1, "KELLY")
        self.assertTrue(pal["colors"])
        row = json.loads(self.conn.execute("SELECT palette FROM characters WHERE name='KELLY'").fetchone()[0])
        self.assertEqual((row["by"], row["ref_sha"]), ("auto", palette.file_sha(self.ref)))
        with mock.patch.object(palette, "extract", side_effect=AssertionError("không trích lại khi ảnh mốc không đổi")):
            palette.character_palette(self.conn, 1, "KELLY")

    def test_person_set_palette_wins(self):
        palette.set_palette(self.conn, 1, "KELLY", ["#2962FF"])
        pal = palette.character_palette(self.conn, 1, "KELLY")
        self.assertEqual([c["hex"] for c in pal["colors"]], ["#2962FF"])
        with self.assertRaises(ValueError):
            palette.set_palette(self.conn, 1, "KELLY", ["xanh"])

    def test_attach_only_when_flag_on_and_one_character(self):
        frame_path = picture(os.path.join(self.dir, "f.png"), BLUE)
        code = {}
        with mock.patch.object(features, "on", return_value=False):
            palette.attach(code, self.conn, 1, frame_path, {"characters": ["Kelly"]})
        self.assertEqual(code, {})
        with mock.patch.object(features, "on", side_effect=lambda n: n == "palette_check"):
            palette.attach(code, self.conn, 1, frame_path, {"characters": ["Kelly"]})
            self.assertEqual(code["_palette"]["status"], "uncertain")
            self.assertTrue(code["_palette"]["missing"])
            other = {}
            palette.attach(other, self.conn, 1, frame_path, {"characters": ["Kelly", "Maxim"]})
            self.assertEqual(other["_palette"]["status"], "not_measurable")

    def test_qc_team_calls_attach(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "core", "qc_team.py"), encoding="utf-8") as f:
            self.assertIn("palette.attach(code, p.conn, pid, frame[\"path\"], frame[\"data\"])", f.read())


if __name__ == "__main__":
    unittest.main()
