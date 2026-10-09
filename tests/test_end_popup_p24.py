"""08/10 dự án #24 (việc 10): popup/icon/chữ quảng cáo cuối phim ghép lên CẢNH CUỐI, không tạo shot nền trống chờ hậu kỳ.
(a) câu trả lời Director THẬT của #24 có 2 shot "nền tối mờ sương, chờ icon … hiện lên ở hậu kỳ" → shot_normalize gộp vào shot cuối;
(b) dựng thật một mp4 ngắn bằng ffmpeg: icon bật lần lượt + chữ tiếng Việt có dấu chồng lên giây cuối (ffprobe + trích khung)."""
import json
import os
import subprocess
import tempfile
import unittest

from core import end_popup, ffmpeg_studio, shot_normalize
from core.db import connect
from core.pipeline import Pipeline

HERE = os.path.join(os.path.dirname(__file__), "fixtures")


def _ffmpeg():
    try:
        return ffmpeg_studio.find_ffmpeg()
    except Exception:  # noqa: BLE001
        return None


class FoldPostOnlyTests(unittest.TestCase):
    def test_real_director_answer_folds_the_two_waiting_shots(self):
        obj = json.load(open(os.path.join(HERE, "director_p24_shots.json"), encoding="utf-8"))
        for s in obj["scenes"][0]["shots"]:
            s["duration_s"] = 2.0
        out, changes = shot_normalize.normalize(obj)
        shots = out["scenes"][0]["shots"]
        self.assertEqual(len(shots), 9)
        self.assertFalse(any(shot_normalize.post_only(s) for s in shots))
        self.assertIn("Trồi Lên", shots[-1]["end_card_note"])
        self.assertEqual(shots[-1]["duration_s"], 6.0)                # its 2 s + the two folded 2 s shots
        self.assertEqual(len(out["end_card"]["folded_shots"]), 2)
        self.assertTrue(any("popup" in c for c in changes))

    def test_a_shot_with_people_is_never_folded(self):
        self.assertFalse(shot_normalize.post_only({"characters": ["KELLY"], "action": "chờ icon hiện ở hậu kỳ"}))
        self.assertFalse(shot_normalize.post_only({"characters": [], "action": "quảng trường vắng, gió thổi"}))


@unittest.skipUnless(_ffmpeg(), "ffmpeg không có trên máy")
class PopupRenderTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image, ImageDraw
        self.dir = tempfile.mkdtemp()
        self.video = os.path.join(self.dir, "in.mp4")
        subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x203040:s=360x640:d=3:r=24",
                        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", self.video], check=True)
        self.icons = []
        for n, colour in (("a", (230, 40, 40, 255)), ("b", (40, 200, 90, 255))):
            im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
            ImageDraw.Draw(im).ellipse([10, 10, 190, 190], fill=colour)
            path = os.path.join(self.dir, f"{n}.png")
            im.save(path)
            self.icons.append(path)
        self.p = Pipeline(connect())

    def test_icons_and_vietnamese_words_pop_over_the_end(self):
        cfg = end_popup.config({"end_popup": {"items": [{"path": self.icons[0], "label": "Hành động Trồi Lên"},
                                                         {"path": self.icons[1], "label": "Tiếng Khóc Ai Oán"}],
                                              "headline": "Hành động sắp ra mắt", "seconds": 2.0, "hold": False}})
        out = os.path.join(self.dir, "out.mp4")
        info = end_popup.apply(self.p.conn, self.video, out, cfg)
        self.assertAlmostEqual(info["start_s"], 1.0, delta=0.1)
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(out), 3.0, delta=0.15)
        self.assertEqual(ffmpeg_studio.probe_size(out), (360, 640))
        from PIL import Image
        frames = {}
        for t in (0.5, 2.9):
            png = os.path.join(self.dir, f"f{t}.png")
            subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-ss", str(t), "-i", out, "-frames:v", "1", png], check=True)
            frames[t] = Image.open(png).convert("RGB")
        if os.environ.get("POPUP_FRAME_OUT"):                             # look at it by eye: POPUP_FRAME_OUT=<folder>
            frames[2.9].save(os.path.join(os.environ["POPUP_FRAME_OUT"], "popup_end.png"))
        import numpy as np
        before, after = (np.asarray(frames[t], dtype=int) for t in (0.5, 2.9))
        self.assertLess(float(before.std(axis=(0, 1)).max()), 3.0)       # plain colour before the popup
        r, g, b = after[..., 0], after[..., 1], after[..., 2]
        red = int(((r > 150) & (g < 90) & (b < 90)).sum())
        green = int(((g > 150) & (r < 90)).sum())
        self.assertGreater(red, 500)                                      # both icons popped by the end
        self.assertGreater(green, 500)
        yellow = int(((r > 225) & (g > 185) & (b < 70)).sum())
        self.assertGreater(yellow, 300)                                   # the headline is drawn in BRIGHT yellow (#FFD400), not dull

    def _pop_wav(self):
        wav = os.path.join(self.dir, "pop.wav")
        subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=900:duration=0.2:sample_rate=48000",
                        "-af", "volume=0.9", wav], check=True)
        return wav

    def _rms(self, path, t, d=0.12):
        import numpy as np
        raw = subprocess.run([_ffmpeg(), "-loglevel", "error", "-ss", str(t), "-t", str(d), "-i", path, "-ac", "1", "-ar", "48000",
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout
        a = np.frombuffer(raw, dtype=np.float32)
        return float(np.sqrt((a ** 2).mean())) if a.size else 0.0

    def test_09_10_default_holds_the_last_frame_so_the_last_shot_is_not_covered(self):
        """Người dùng 09/10 (#24: popup 3,5 s che gần hết shot khóc 0,58 s): mặc định giữ khung cuối thêm `seconds`, popup nằm trên đó."""
        cfg = end_popup.config({"end_popup": {"items": [{"path": self.icons[0], "label": "a"}], "headline": "Sắp ra mắt", "seconds": 2.0,
                                              "sound": False}})
        self.assertTrue(cfg["hold"])
        out = os.path.join(self.dir, "held.mp4")
        info = end_popup.apply(self.p.conn, self.video, out, cfg)
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(out), 5.0, delta=0.15)        # 3 s clip + 2 s held frame
        self.assertAlmostEqual(info["start_s"], 3.0, delta=0.1)                         # the popup starts after the last shot
        self.assertAlmostEqual(info["held_s"], 2.0)
        from PIL import Image
        png = os.path.join(self.dir, "before.png")
        subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-ss", "2.9", "-i", out, "-frames:v", "1", png], check=True)
        src = os.path.join(self.dir, "src.png")
        subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-ss", "2.9", "-i", self.video, "-frames:v", "1", src], check=True)
        a, b = Image.open(png).convert("RGB").resize((36, 64)), Image.open(src).convert("RGB").resize((36, 64))
        diff = sum(abs(x - y) for p_, q in zip(a.getdata(), b.getdata()) for x, y in zip(p_, q)) / (36 * 64 * 3)
        self.assertLess(diff, 8)                                                         # the last shot itself is untouched

    def test_08_10_caps_bright_yellow_and_a_pop_per_icon_over_a_silent_video(self):
        """Góp ý 08/10: VIẾT HOA giữ dấu, vàng sáng, tiếng pop đúng lúc mỗi icon bật; video không tiếng → tạo track."""
        self.assertEqual(end_popup.caps("Hành động sắp ra mắt"), "HÀNH ĐỘNG SẮP RA MẮT")
        self.assertEqual(end_popup.caps("tiếng khóc ai oán"), "TIẾNG KHÓC AI OÁN")
        silent = os.path.join(self.dir, "silent.mp4")
        subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x203040:s=360x640:d=3:r=24",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", silent], check=True)
        self.assertFalse(ffmpeg_studio.has_audio(silent))
        cfg = end_popup.config({"end_popup": {"items": [{"path": self.icons[0], "label": "Hành động Trồi Lên"},
                                                         {"path": self.icons[1], "label": "Tiếng Khóc Ai Oán"}],
                                              "headline": "Hành động sắp ra mắt", "seconds": 2.0, "sound": self._pop_wav(), "hold": False}})
        self.assertTrue(cfg["uppercase"])
        self.assertEqual(cfg["headline_color"], "#FFD400")
        out = os.path.join(self.dir, "pop.mp4")
        info = end_popup.apply(self.p.conn, silent, out, cfg)
        self.assertEqual(info["pops_s"], [1.0, 1.6])
        self.assertTrue(ffmpeg_studio.has_audio(out))
        self.assertAlmostEqual(ffmpeg_studio.probe_duration(out), 3.0, delta=0.15)
        self.assertLess(self._rms(out, 0.3), 0.003)                        # silence before the popup
        self.assertGreater(self._rms(out, 1.02), 0.03)                     # pop 1 as icon 1 pops
        self.assertGreater(self._rms(out, 1.62), 0.03)                     # pop 2 as icon 2 pops
        self.assertLess(self._rms(out, 1.35), 0.003)                       # nothing in between

    def test_pop_is_mixed_into_the_existing_sound_not_replacing_it(self):
        tone = os.path.join(self.dir, "tone.mp4")
        subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x203040:s=360x640:d=3:r=24",
                        "-f", "lavfi", "-i", "sine=frequency=220:duration=3:sample_rate=48000", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", tone], check=True)
        cfg = end_popup.config({"end_popup": {"items": [{"path": self.icons[0], "label": "a"}], "seconds": 2.0, "hold": False, "sound": self._pop_wav(),
                                              "sound_volume": 1.0}})
        out = os.path.join(self.dir, "mix.mp4")
        end_popup.apply(self.p.conn, tone, out, cfg)
        before, at = self._rms(tone, 1.02), self._rms(out, 1.02)
        self.assertGreater(self._rms(out, 0.3), 0.03)                     # the video's own sound is kept
        self.assertGreater(at, before * 1.2)                              # + the pop on top

    def test_no_pop_when_turned_off_and_missing_pop_file_is_an_error(self):
        cfg = end_popup.config({"end_popup": {"items": [{"path": self.icons[0], "label": "a"}], "sound": False}})
        self.assertIsNone(end_popup.pop_sound(self.p.conn, cfg))
        cfg = end_popup.config({"end_popup": {"items": [{"path": self.icons[0], "label": "a"}], "sound": os.path.join(self.dir, "x.wav")}})
        with self.assertRaises(ValueError):
            end_popup.apply(self.p.conn, self.video, os.path.join(self.dir, "o.mp4"), cfg)

    def test_missing_icon_is_an_error_not_a_silent_gap(self):
        cfg = end_popup.config({"end_popup": {"items": [{"path": os.path.join(self.dir, "none.png"), "label": "x"}]}})
        with self.assertRaises(ValueError):
            end_popup.apply(self.p.conn, self.video, os.path.join(self.dir, "o.mp4"), cfg)


class PopupSettingsTests(unittest.TestCase):
    def test_suggest_from_icon_props_and_saved_for_the_render(self):
        from PIL import Image
        from core import assets, delivery
        p = Pipeline(connect())
        pid = p.create_project("p24", game="FF")
        p.conn.execute("UPDATE projects SET script_text=? WHERE id=?", ('… dòng chữ lớn "Hành động sắp ra mắt".', pid))
        d = tempfile.mkdtemp()
        for name in ("ICON HÀNH ĐỘNG TRỒI LÊN", "ICON HÀNH ĐỘNG TIẾNG KHÓC AI OÁN"):
            aid = assets.create(p.conn, "FF", "prop", name, project_id=pid)
            path = os.path.join(d, f"{aid}.png")
            Image.new("RGBA", (64, 64), (255, 0, 0, 255)).save(path)
            p.conn.execute("INSERT INTO asset_images (asset_id, path, role, status) VALUES (?, ?, 'object', 'approved')", (aid, path))
            assets.attach(p.conn, pid, aid)
        p.conn.commit()
        cfg = end_popup.suggest(p.conn, pid, p.project(pid)["script_text"])
        self.assertEqual([i["label"] for i in cfg["items"]], ["Hành động trồi lên", "Hành động tiếng khóc ai oán"])
        self.assertEqual(cfg["headline"], "Hành động sắp ra mắt")
        before = delivery.render_hash(delivery.get_settings(p, pid))
        delivery.save_settings(p, pid, dict(delivery.get_settings(p, pid), end_popup=cfg))
        got = delivery.get_settings(p, pid)
        self.assertEqual(end_popup.config(got)["headline"], "Hành động sắp ra mắt")
        self.assertNotEqual(delivery.render_hash(got), before)            # the cut without the popup is "cũ"


if __name__ == "__main__":
    unittest.main()
