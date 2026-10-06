"""S14.48 (ý 2 từ tài liệu 'Prompt Spider' 06/10): màu chính nhân vật đo bằng CODE (0 USD), sau cờ `palette_check` TẮT; chỉ ghi chú
'uncertain', không tự từ chối. Người dùng hỏi 06/10 "màu có bị thời tiết, đèn ảnh hưởng, dễ báo nhầm?" → đo NỚI: cân trắng + so sắc màu
(không so độ sáng), cảnh đêm / hoàng hôn / quá tối không so, bỏ cận mặt, so TRONG CẢNH, bỏ so ảnh mốc khi nhân vật mặc trang phục riêng.
Không có bộ dò mặt trên máy test → thay bằng hộp mặt cố định; trời đọc 'day' trừ khi test nói khác."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import features, palette, qc_team
from core.db import connect

RED, BLUE, BLACK, GRAY, SKIN = (192, 57, 43), (41, 98, 255), (25, 25, 28), (150, 150, 150), (224, 172, 140)
FACE = (0.40, 0.10, 0.60, 0.30)          # left, top, right, bottom (fractions)


def picture(path, torso, size=(400, 600), face=FACE, bg=GRAY, scale=1.0, cast=(1.0, 1.0, 1.0)):
    """A grey frame, a skin face box, a torso of colour `torso` under it; then the whole picture × scale × colour cast (the light)."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    w, h = size
    l, t, r, b = face
    d.rectangle([l * w, t * h, r * w, b * h], fill=SKIN)
    fw = (r - l) * w
    d.rectangle([l * w - 0.6 * fw, b * h, r * w + 0.6 * fw, min(h, b * h + 2.2 * (b - t) * h)], fill=torso)
    if scale != 1.0 or cast != (1.0, 1.0, 1.0):
        im = Image.eval(im, lambda v: v)
        px = im.load()
        for x in range(w):
            for y in range(h):
                px[x, y] = tuple(int(min(255, px[x, y][i] * scale * cast[i])) for i in range(3))
    im.save(path)
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        for p in (mock.patch.object(palette, "_faces", lambda path: [FACE]),
                  mock.patch.object(palette, "_sky", lambda path: {"reading": "day"})):
            p.start()
            self.addCleanup(p.stop)

    def pic(self, name, torso, **kw):
        return picture(os.path.join(self.dir, name), torso, **kw)


class MeasureTests(Base):
    def test_hex_and_delta_e(self):
        self.assertEqual(palette.to_hex(RED), "#C0392B")
        self.assertEqual(palette.from_hex("#c0392b"), RED)
        self.assertLess(palette.delta_e(RED, (190, 60, 45)), 5)
        with self.assertRaises(ValueError):
            palette.from_hex("đỏ")

    def test_extract_finds_the_torso_colour(self):
        top = palette.extract(self.pic("ref.png", RED))["colors"][0]
        self.assertEqual(palette._matches([RED] * 4, palette.from_hex(top["hex"])), 1.0)     # cùng sắc đỏ (đã cân trắng)
        self.assertEqual(palette._matches([BLUE] * 4, palette.from_hex(top["hex"])), 0.0)
        self.assertGreater(top["share"], 0.4)

    def test_same_outfit_ok_other_colour_flagged_never_certain(self):
        pal = palette.extract(self.pic("ref.png", RED))
        ok = palette.check(self.pic("same.png", RED), pal)
        self.assertEqual((ok["status"], ok["missing"]), ("uncertain", []))
        bad = palette.check(self.pic("blue.png", BLUE), pal)
        self.assertEqual(bad["status"], "uncertain")
        self.assertTrue(bad["missing"])
        self.assertIn("lệch", bad["note"])

    def test_dimmer_light_and_colour_cast_do_not_raise_a_false_alarm(self):
        pal = palette.extract(self.pic("ref.png", RED))
        dim = palette.check(self.pic("dim.png", RED, scale=0.55), pal)               # tối hơn (vẫn trên ngưỡng quá tối)
        self.assertEqual(dim["missing"], [], dim)
        tinted = palette.check(self.pic("tint.png", RED, cast=(0.85, 1.0, 1.2)), pal)    # đèn ngả xanh, trời vẫn đọc 'day'
        self.assertEqual(tinted["missing"], [], tinted)

    def test_black_jacket_under_dim_light_still_matches(self):
        pal = palette.extract(self.pic("ref.png", BLACK))
        self.assertEqual(palette.check(self.pic("dimblack.png", BLACK, scale=0.7, bg=(200, 200, 200)), pal)["missing"], [])

    def test_night_sunset_dark_and_close_up_are_not_measured(self):
        pal = palette.extract(self.pic("ref.png", RED))
        with mock.patch.object(palette, "_sky", lambda path: {"reading": "warm"}):
            self.assertIn("ấm", palette.check(self.pic("sunset.png", BLUE), pal)["note"])
        with mock.patch.object(palette, "_sky", lambda path: {"reading": "dark"}):
            self.assertEqual(palette.check(self.pic("night.png", BLUE), pal)["status"], "not_measurable")
        dark = palette.check(self.pic("dark.png", BLUE, scale=0.25), pal)
        self.assertEqual(dark["status"], "not_measurable")
        self.assertIn("tối", dark["note"])
        with mock.patch.object(palette, "_faces", lambda path: [(0.3, 0.1, 0.7, 0.6)]):
            cu = palette.check(self.pic("cu.png", BLUE, face=(0.3, 0.1, 0.7, 0.6)), pal)
        self.assertEqual(cu["status"], "not_measurable")
        self.assertIn("cận mặt", cu["note"])

    def test_two_faces_or_no_detector_say_why(self):
        pal = palette.extract(self.pic("ref.png", RED))
        with mock.patch.object(palette, "_faces", lambda path: [FACE, (0.1, 0.1, 0.2, 0.2)]):
            self.assertIn("mặt", palette.check(self.pic("two.png", RED), pal)["note"])
        with mock.patch.object(palette, "_faces", lambda path: None):
            self.assertEqual(palette.check(self.pic("x.png", RED), pal)["status"], "not_measurable")
        self.assertEqual(palette.check(self.pic("y.png", RED), {"colors": []})["status"], "not_measurable")


class SceneTests(Base):
    def frame(self, job, torso, who="Kelly", **kw):
        return {"job_id": job, "path": self.pic(f"f{job}.png", torso, **kw), "data": {"characters": [who]}}

    def test_the_odd_frame_out_is_pointed_at(self):
        frames = [self.frame(1, RED), self.frame(2, RED, scale=0.7), self.frame(3, RED), self.frame(4, BLUE)]
        got = palette.scene_check(frames)
        self.assertTrue(got[4]["outlier"])
        self.assertIn("khác", got[4]["note"])
        self.assertFalse(any(got[j]["outlier"] for j in (1, 2, 3)))

    def test_two_frames_disagreeing_do_not_blame_one(self):
        got = palette.scene_check([self.frame(1, RED), self.frame(2, BLUE)])
        self.assertFalse(got[1]["outlier"] or got[2]["outlier"])
        self.assertIn("khác màu", got[1]["note"])

    def test_scene_light_does_not_matter_and_crowds_are_skipped(self):
        with mock.patch.object(palette, "_sky", lambda path: {"reading": "dark"}):          # cùng cảnh = cùng ánh sáng
            got = palette.scene_check([self.frame(1, RED, scale=0.6), self.frame(2, RED, scale=0.6), self.frame(3, RED, scale=0.6)])
        self.assertFalse(any(v["outlier"] for v in got.values()))
        crowd = {"job_id": 9, "path": self.pic("c.png", BLUE), "data": {"characters": ["Kelly", "Maxim"]}}
        self.assertNotIn(9, palette.scene_check([crowd, self.frame(1, RED), self.frame(2, RED)]))


class StoreAndQcTeamTests(Base):
    def setUp(self):
        super().setUp()
        self.conn = connect()
        self.conn.execute("INSERT INTO projects (name, created_at) VALUES ('p', '2026-10-06T00:00:00Z')")
        self.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (1, 'KELLY', 'nữ')")
        self.conn.commit()
        self.ref = self.pic("ref.png", RED)
        link = mock.patch.object(palette, "_reference_path", lambda conn, pid, name: self.ref if name == "KELLY" else None)
        link.start()
        self.addCleanup(link.stop)

    def test_flag_exists_and_is_off(self):
        self.assertIn("palette_check", features.FEATURES)
        self.assertFalse(features.FEATURES["palette_check"]["verified"])

    def test_palette_is_extracted_once_per_reference_and_stored(self):
        self.assertTrue(palette.character_palette(self.conn, 1, "Kelly")["colors"])
        row = json.loads(self.conn.execute("SELECT palette FROM characters WHERE name='KELLY'").fetchone()[0])
        self.assertEqual((row["by"], row["ref_sha"]), ("auto", palette.file_sha(self.ref)))
        with mock.patch.object(palette, "extract", side_effect=AssertionError("không trích lại khi ảnh mốc không đổi")):
            palette.character_palette(self.conn, 1, "KELLY")

    def test_person_set_palette_wins(self):
        palette.set_palette(self.conn, 1, "KELLY", ["#2962FF"])
        self.assertEqual([c["hex"] for c in palette.character_palette(self.conn, 1, "KELLY")["colors"]], ["#2962FF"])
        with self.assertRaises(ValueError):
            palette.set_palette(self.conn, 1, "KELLY", ["xanh"])

    def test_project_outfit_skips_the_reference_comparison(self):
        with mock.patch.object(palette, "_has_outfit", return_value=True):
            pal = palette.character_palette(self.conn, 1, "KELLY")
        self.assertEqual(pal["colors"], [])
        self.assertIn("trang phục riêng", pal["note"])
        self.assertEqual(palette.check(self.pic("b.png", BLUE), pal)["status"], "not_measurable")

    def test_attach_only_when_flag_on_and_one_character(self):
        frame_path = self.pic("f.png", BLUE)
        code = {}
        with mock.patch.object(features, "on", return_value=False):
            palette.attach(code, self.conn, 1, frame_path, {"characters": ["Kelly"]})
        self.assertEqual(code, {})
        with mock.patch.object(features, "on", side_effect=lambda n: n == "palette_check"):
            palette.attach(code, self.conn, 1, frame_path, {"characters": ["Kelly"]})
            self.assertTrue(code["_palette"]["missing"])
            other = {}
            palette.attach(other, self.conn, 1, frame_path, {"characters": ["Kelly", "Maxim"]})
            self.assertEqual(other["_palette"]["status"], "not_measurable")

    def test_result_reaches_the_person_note(self):
        """Lỗi bản đầu S14.48: review_frame bỏ mọi khóa '_' → _palette không bao giờ tới người. Nay kết quả giữ ở res['palette']."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "core", "qc_team.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn('"palette": code.get("_palette")', src)
        self.assertIn("palette.scene_check(", src)
        base = {"verdict": "ok", "fails": [], "arbiter": [], "plan_conflicts": []}
        self.assertNotIn("Màu", qc_team.note_of({**base, "palette": {"missing": [], "note": "khớp"}}))
        self.assertIn("lệch màu", qc_team.note_of({**base, "palette": {"missing": ["#C0392B"], "note": "có thể lệch màu trang phục"}}))
        self.assertIn("khác", qc_team.note_of({**base, "palette_scene": {"outlier": True, "note": "KELLY: màu trang phục khác 3 khung"}}))


if __name__ == "__main__":
    unittest.main()
