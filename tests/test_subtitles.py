import json
import os
import shutil
import subprocess
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from core import autopilot, dialogue, ffmpeg_studio, llm_runner, subtitles
from core.db import connect
from core.pipeline import Pipeline
from core.subtitles import Cue, Font, SubtitleError
from tests.test_autopilot import Setup, fake_render
from tests.test_keep_audio import ffmpeg_available

APP = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
VN = frozenset(ord(c) for c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ếệỗơưăằẳẵặđĐẤỨ.,!?")
LATIN = frozenset(ord(c) for c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ .,!?")


def font(name, cmap, path="x.ttf"):
    return Font(path, name, name, all(ord(c) in cmap for c in "ếệỗơưăđ"), "test", frozenset(cmap), name)


def clips_with_dialogue(test, lines=None):
    """A project whose scenes have fake clip files of a known length and dialogue in the scene text."""
    ctx = test.build()
    p, pid = test.p, test.pid
    os.makedirs(os.path.join(test.data, str(pid), "videos"), exist_ok=True)
    for r in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        with open(os.path.join(test.data, str(pid), "videos", f"{r['idx']:02d}.mp4"), "wb") as f:
            f.write(b"not a real video")                             # probe fails -> the planned duration is used
        data = json.loads(r["data"] or "{}")
        data["text"] = (lines or {}).get(r["idx"], "" if lines else data.get("text", ""))
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), r["id"]))
        p.conn.execute("DELETE FROM motion_prompts WHERE scene_id=?", (r["id"],))
        p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec, state) VALUES (?,?,?,?)",
                       (r["id"], "push in", 6, "approved"))
    p.conn.commit()
    return ctx


class CueTests(Setup):
    def test_dialogue_lines_are_timed_inside_their_own_clip_on_the_final_timeline(self):
        clips_with_dialogue(self, {1: "LYRA: Xin chào các bạn.\nKAEL: Chào cô.", 2: "Không có thoại.", 3: "ORIN: Bóng Đêm đã tỉnh giấc."})
        cues = subtitles.build_cues(self.p, self.data, self.pid)
        self.assertEqual([c.speaker for c in cues], ["LYRA", "KAEL", "ORIN"])
        first, second, third = cues
        self.assertTrue(0 < first.start < first.end <= second.start < second.end <= 6)      # both lines inside clip 1 (0-6 s)
        self.assertGreaterEqual(third.start, 12)                                             # scene 3 starts after clips 1 and 2 (12 s)
        self.assertTrue(all(c.end - c.start >= 0.5 for c in cues))

    def test_a_crossfade_pulls_later_clips_earlier_by_the_overlap(self):
        clips_with_dialogue(self, {1: "LYRA: Một.", 2: "KAEL: Hai.", 3: "ORIN: Ba."})
        cut = subtitles.build_cues(self.p, self.data, self.pid, "cut")
        fade = subtitles.build_cues(self.p, self.data, self.pid, "crossfade", 1.0)
        self.assertAlmostEqual(cut[2].start - fade[2].start, 2.0, places=1)                  # two overlaps of 1 s

    def test_srt_and_ass_formats(self):
        cues = [Cue(0.5, 2.25, "Có thứ gì đó.", "LYRA", 1), Cue(3661.5, 3663, "Dòng hai", "KAEL", 2)]
        srt = subtitles.to_srt(cues)
        self.assertIn("1\n00:00:00,500 --> 00:00:02,250\nCó thứ gì đó.", srt)
        self.assertIn("01:01:01,500 --> 01:01:03,000", srt)
        self.assertIn("Lyra: Có thứ gì đó.", subtitles.to_srt(cues, show_speaker=True))
        ass = subtitles.to_ass(cues, 1080, 1920, font("GFF Latin Bold", VN), "M", "bottom", "yellow")
        self.assertIn("PlayResX: 1080", ass)
        self.assertIn("Style: Default,GFF Latin Bold,70", ass)                               # 6.5% of the shorter side (1080)
        self.assertIn("&H0066E0FF", ass)                                                     # yellow, BGR order
        self.assertIn("Dialogue: 0,00:00:00.50,00:00:02.25,Default", ass)

    def test_long_lines_are_wrapped_in_balanced_pieces(self):
        text = "Có thứ gì đó đang theo chúng ta hãy ở yên sau lưng ta đừng chạy"
        wrapped = subtitles.wrap_text(text, 30)
        lines = wrapped.split("\n")
        self.assertGreaterEqual(len(lines), 2)
        self.assertTrue(all(len(l) <= 40 for l in lines))
        self.assertEqual(" ".join(lines), text)
        self.assertEqual(subtitles.wrap_text("Ngắn.", 30), "Ngắn.")


class TranslationTests(unittest.TestCase):
    def test_translation_keeps_timing_and_needs_the_api(self):
        cues = [Cue(0.5, 2, "Xin chào", "LYRA", 1), Cue(2.5, 4, "Tạm biệt", "KAEL", 1)]
        out = subtitles.translate(llm_runner.MockLlm(), cues, "en")
        self.assertEqual([c.text for c in out], ["[English] Xin chào", "[English] Tạm biệt"])
        self.assertEqual([(c.start, c.end, c.speaker) for c in out], [(c.start, c.end, c.speaker) for c in cues])
        self.assertIs(subtitles.translate(None, cues, "src"), cues)                            # original language needs no model
        with self.assertRaises(SubtitleError):
            subtitles.translate(None, cues, "en")

    def test_a_reply_with_the_wrong_number_of_lines_is_rejected(self):
        class Short:
            def complete(self, prompt, images=()):
                return llm_runner.LlmReply('{"cues": [{"id": 1, "text": "x"}]}', 1, 1)

        with self.assertRaises(llm_runner.LlmError):
            subtitles.translate(Short(), [Cue(0, 1, "a"), Cue(1, 2, "b")], "en")


class FontTests(unittest.TestCase):
    def test_a_font_that_cannot_draw_the_language_is_swapped_for_one_that_can_and_the_person_is_told(self):
        gff = font("GFF Latin Bold", VN)
        thai = font("Leelawadee UI", set(VN) | {ord(c) for c in "สวัสดี"})
        chosen, note = subtitles.font_for_text(gff, [gff, thai], "Tiếng Việt")
        self.assertIs(chosen, gff)
        self.assertIsNone(note)
        chosen, note = subtitles.font_for_text(gff, [gff, thai], "สวัสดี")
        self.assertIs(chosen, thai)
        self.assertIn("GFF Latin Bold", note)
        chosen, note = subtitles.font_for_text(gff, [gff], "สวัสดี")
        self.assertIn("Không có font nào", note)

    def test_the_default_is_gff_latin_bold_when_it_is_installed_else_any_vietnamese_capable_font(self):
        gff, arial, latin = font("GFF Latin Bold", VN), font("Arial", VN), font("Plain", LATIN)
        self.assertIs(subtitles.default_font([arial, gff]), gff)
        self.assertIs(subtitles.default_font([latin, arial]), arial)
        self.assertEqual(subtitles.missing_chars(latin, "ếa"), "ế")

    def test_uploaded_fonts_are_checked_and_listed(self):
        tmp = tempfile.mkdtemp()
        os.environ["FONT_DIR"] = tmp
        try:
            with self.assertRaises(SubtitleError):
                subtitles.save_uploaded_font("x.exe", b"abc")
            with self.assertRaises(SubtitleError):
                subtitles.save_uploaded_font("broken.ttf", b"this is not a font")
            self.assertFalse(os.path.exists(os.path.join(tmp, "broken.ttf")))                # the bad file is not kept
        finally:
            os.environ.pop("FONT_DIR", None)

    @unittest.skipUnless(any(f.family == "GFF Latin Bold" for f in subtitles.discover()), "GFF font not installed on this machine")
    def test_the_gff_fonts_of_this_machine_are_found_and_the_default_is_gff_bold(self):
        fonts = subtitles.discover()
        self.assertEqual(subtitles.default_font(fonts).family, "GFF Latin Bold")
        self.assertTrue(fonts[0].family.startswith("GFF"))                                    # GFF first in the list
        self.assertTrue(subtitles.default_font(fonts).vietnamese)


@unittest.skipUnless(ffmpeg_available() and any(f.family == "GFF Latin Bold" for f in subtitles.discover()),
                     "needs ffmpeg with libass and the GFF font")
class BurnTests(unittest.TestCase):
    def test_burned_video_uses_exactly_the_chosen_font_and_keeps_audio(self):
        tmp = tempfile.mkdtemp()
        ff = ffmpeg_studio.find_ffmpeg()
        src = os.path.join(tmp, "in.mp4")
        subprocess.run([ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=0x3a4a6a:s=540x960:d=2:r=24", "-f", "lavfi", "-i",
                        "sine=f=300:d=2", "-c:a", "aac", "-shortest", "-pix_fmt", "yuv420p", src], check=True)
        fonts = subtitles.discover()
        gff = subtitles.font_by_family(fonts, "GFF Latin Bold")
        black = subtitles.font_by_family(fonts, "GFF Latin Black")
        for f in (gff, black):
            res = subtitles.burn(src, [Cue(0.2, 1.8, "Có thứ gì đó đang theo chúng ta", "LYRA", 1)], os.path.join(tmp, f"{f.family}.mp4"), f)
            self.assertTrue(res["font_verified"], f.family)                                   # libass really used THIS file, not Arial
            self.assertTrue(os.path.exists(res["srt"]))
            self.assertTrue(ffmpeg_studio.has_audio(res["video"]))
        with self.assertRaises(SubtitleError):
            subtitles.burn(src, [], os.path.join(tmp, "none.mp4"), gff)


class AutopilotSubtitleTests(Setup):
    def test_when_switched_on_the_automatic_run_adds_subtitles_after_the_render_and_a_failure_never_loses_the_video(self):
        ctx = clips_with_dialogue(self, {1: "LYRA: Xin chào."})
        calls = []
        ctx.subtitle = lambda p, pid, data, video, llm: calls.append(video) or {"video": video + ".sub.mp4", "cues": 1}
        subtitles.save_settings(self.p, self.pid, {**subtitles.DEFAULTS, "enabled": True, "lang": "en"})
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.DONE)
        self.assertEqual(len(calls), 1)
        self.assertIn("+ phụ đề", autopilot.status(self.p, self.pid)["note"])

        ctx2 = clips_with_dialogue(self)
        ctx2.subtitle = lambda *a: (_ for _ in ()).throw(SubtitleError("không có font"))
        self.p.conn.execute("UPDATE projects SET autopilot_state=NULL WHERE id=?", (self.pid,))
        self.p.conn.commit()
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx2), autopilot.DONE)    # video is there, subtitles failed
        self.assertTrue(self.p.conn.execute("SELECT 1 FROM diag_events WHERE code='subtitles'").fetchone())

    def test_default_settings_leave_the_automatic_run_untouched(self):
        ctx = clips_with_dialogue(self)
        self.assertFalse(subtitles.get_settings(self.p, self.pid)["enabled"])
        self.assertIsNone(autopilot.default_subtitle(self.p, self.pid, self.data, "whatever.mp4", None))
        autopilot.start(self.p, self.pid)
        self.assertEqual(autopilot.run_until_done(self.p, self.pid, ctx), autopilot.DONE)
        self.assertNotIn("phụ đề", autopilot.status(self.p, self.pid)["note"])

    def test_settings_are_saved_per_project_and_unknown_keys_are_ignored(self):
        self.build()
        self.assertEqual(subtitles.get_settings(self.p, self.pid), subtitles.DEFAULTS)
        subtitles.save_settings(self.p, self.pid, {"lang": "th", "size": "L", "bogus": 1})
        got = subtitles.get_settings(self.p, self.pid)
        self.assertEqual((got["lang"], got["size"], got["pos"]), ("th", "L", "bottom"))
        self.assertNotIn("bogus", got)


class MergedStepTests(unittest.TestCase):
    def test_music_and_render_are_one_step_with_the_subtitle_panel(self):
        tmp = tempfile.mkdtemp()
        os.environ.update({"PIPELINE_DB": os.path.join(tmp, "m.sqlite"), "PIPELINE_DATA": os.path.join(tmp, "projects")})
        try:
            Pipeline(connect(os.environ["PIPELINE_DB"])).create_project("merged")
            at = AppTest.from_file(APP, default_timeout=40)
            at.query_params["step"] = "5a"                                                   # old deep links still work
            at.run()
            self.assertFalse(at.exception)
            options = list(at.radio(key="step").options)
            self.assertEqual(len(options), 9)
            self.assertFalse(any(o.startswith(("5a", "5b")) for o in options))
            self.assertTrue(any(o.startswith("5 · Nhạc nền & Ghép video") for o in options))
            self.assertEqual(at.radio(key="step").value, next(o for o in options if o.startswith("5 ·")))
            self.assertTrue(any("Phụ đề tự động" in e.label for e in at.expander))
        finally:
            os.environ.pop("PIPELINE_DB", None)
            os.environ.pop("PIPELINE_DATA", None)


if __name__ == "__main__":
    unittest.main()
